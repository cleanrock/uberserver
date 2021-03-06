import thread, time, sys, os, socket

import base64
try: from hashlib import md5
except: md5 = __import__('md5').new

import traceback
from Protocol import Channel, Protocol

from tasserver import LegacyChannels, LegacyUsers

separator = '-'*60

class DataHandler:
    def __init__(self):
        self.local_ip = None
        self.online_ip = None
        self.session_id = 0
        self.dispatcher = None
        self.console_buffer = []
        self.port = 8200
        self.natport = self.port+1
        self.dbtype = 'lan'
        self.lanadmin = {'username':'', 'password':''}
        self.latestspringversion = '*'
        self.log = False
        self.server = 'TASServer'
        self.server_version = 0.35
        self.sighup = False
        
        self.chanserv = None
        self.userdb = None
        self.engine = None
        self.tsbanurl = None
        self.channelfile = None
        self.protocol = None
        self.updatefile = None
        self.trusted_proxyfile = None
        
        self.max_threads = 25
        self.sqlurl = 'sqlite:///sqlite.txt'
        self.randomflags = False
        self.nextbattle = 0
        self.SayHooks = __import__('SayHooks')
        self.censor = True
        self.motd = None
        self.updates = {}
        self.running = True
        self.output = None
        
        self.trusted_proxies = []
        
        self.start_time = time.time()
        self.channels = {}
        self.chan_alias = {}
        self.usernames = {}
        self.clients = {}
        self.db_ids = {}
        self.battles = {}
        thread.start_new_thread(self.event_loop, ())
    
    def parseArgv(self, argv):
        'parses command-line options'
        args = {'ignoreme':[]}
        mainarg = 'ignoreme'

        tempargv = list(argv)
        while tempargv:
            arg = tempargv.pop(0)
            if arg.startswith('-'):
                mainarg = arg.lstrip('-').lower()

                if mainarg in ['g', 'loadargs']:
                    try:
                        name = tempargv[0]
                        if name.startswith('-'): raise Exception
                        f = file(name, 'r')
                        lines = f.read().split('\n')
                        f.close()

                        tempargv += ' '.join(lines).split(' ')
                    except:
                        pass

                args[mainarg] = []
            else:
                args[mainarg].append(arg)
        del args['ignoreme']

        for arg in args:
            argp = args[arg]
            if arg in ['h', 'help']:
                print 'Usage: server.py [OPTIONS]...'
                print 'Starts uberserver.'
                print
                print 'Options:'
                print '  -h, --help'
                print '      { Displays this screen then exits }'
                print '  -p, --port number'
                print '      { Server will host on this port (default is 8200) }'
                print '  -n, --natport number'
                print '      { Server will use this port for NAT transversal (default is 8201) }'
                print '  -l, --lan'
                print '      { Users do not need to be registered to login - breaks rudimentary features like channel ops/founders, channel/battle bans, etc. }'
                print '  -a, --lanadmin username password [hash] }'
                print '      { Hardcoded admin account for LAN. If third arg reads "hash" it will apply the standard hash algorithm to the supplied password }'
                print '  -g, --loadargs filename'
                print '      { Reads additional command-line arguments from file }'
                print '  -r  --randomflags'
                print '      { Randomizes country codes (flags) }'
                print '  -o, --output /path/to/file.log'
                print '      { Writes console output to file (for logging) }'
                print '  -u, --sighup'
                print '      { Reload the server on SIGHUP (if SIGHUP is supported by OS) }'
                print '  -v, --latestspringversion version'
                print '      { Sets latest Spring version to this string. Defaults to "*" }'
                print '  -m, --maxthreads number'
                print '      { Uses the specified number of threads for handling clients }'
                print '  -s, --sqlurl SQLURL'
                print '      { Uses SQL database at the specified sqlurl for user, channel, and ban storage. }'
                print '  -c, --no-censor'
                print '      { Disables censoring of #main, #newbies, and usernames (default is to censor) }'
                print '  --accounts /path/to/accounts.txt'
                print '      { Path to accounts.txt. For using the legacy TASServer account database. }'
                print '  --tsbans SQLURL'
                print '      { Uses SQL database at the specified sqlurl as a legacy TASServer ban database. } '
                print '  --channels /path/to/settings.xml'
                print '      { Path to ChanServ settings.xml, for using the legacy ChanServ channel database. }'
                print '  --updates /path/to/updates.txt'
                print '     { Path to updates.txt, for using Spring update system. }'
                print '  --proxies /path/to/proxies.txt'
                print '     { Path to proxies.txt, for trusting proxies to pass real IP through local IP }'
                print 'SQLURL Examples:'
                #print '  "sqlite:///:memory:" or "sqlite:///"'
                #print '     { both make a temporary database in memory }'
                print '  "sqlite:////absolute/path/to/database.txt"'
                print '     { uses a database in the file specified }'
                print '  "sqlite:///relative/path/to/database.txt"'
                print '     { note sqlite is slower than a real SQL server }'
                print '  "mysql://user:password@server:port/database"'
                print '     { requires the MySQLdb module }'
                print '  "oracle://user:password@server:port/database"'
                print '     { requires the cx_Oracle module }'
                print '  "postgres://user:password@server:port/database"'
                print '     { requires the psycopg2 module }'
                print '  "mssql://user:password@server:port/database"'
                print '     { requires pyodbc (recommended) or adodbapi or pymssql }'
                print '  "firebird://user:password@server:port/database"'
                print '     { requires the kinterbasdb module }'
                print
                print 'Usage example (this is what the test server uses at the moment):'
                print ' server.py -p 8300 -n 8301'
                print
                exit()
            if arg in ['p', 'port']:
                try: self.port = int(argp[0])
                except: print 'Invalid port specification'
            elif arg in ['n', 'natport']:
                try: self.natport = int(argp[0])
                except: print 'Invalid NAT port specification'
            elif arg in ['l', 'lan']:
                self.dbtype = 'lan'
            elif arg in ['a', 'lanadmin']:
                try:
                    if len(argp) > 2:
                        if argp[2] == 'hash':
                            m = md5(argp[1])
                            argp[1] = base64.b64encode(m.digest())
                    self.lanadmin = {'username':argp[0], 'password':argp[1]}
                except: print 'Invalid LAN admin specified'
            elif arg in ['r', 'randomcc']:
                try: self.randomflags = True
                except: print 'Error enabling random flags. (weird)'
            elif arg in ['o', 'output']:
                try:
                    self.output = file(argp[0], 'w')
                    print 'Logging enabled at: %s' % argp[0]
                    self.log = True
                except: print 'Error specifying log location'
            elif arg in ['u', 'sighup']:
                self.sighup = True
            elif arg in ['v', 'latestspringversion']:
                try: self.latestspringversion = argp[0] # ' '.join(argp) # shouldn't have spaces
                except: print 'Error specifying latest spring version'
            elif arg in ['m', 'maxthreads']:
                try: self.max_threads = int(argp[0])
                except: print 'Error specifing max threads'
            elif arg in ['s', 'sqlurl']:
                try:
                    self.sqlurl = argp[0]
                    self.dbtype = 'sql'
                except:
                    print 'Error specifying SQL URL'
            elif arg in ['c', 'no-censor']:
                self.censor = False
            elif arg == 'accounts':
                try:
                    self.engine = argp[0]
                    open(self.engine, 'r').close()
                    self.dbtype = 'legacy'
                except:
                    print 'Error opening legacy accounts.txt database.'
            elif arg == 'tsbans':
                self.tsbanurl = argp[0]
            elif arg == 'channels':
                try:
                    self.channelfile = argp[0]
                    open(self.channelfile, 'r').close()
                except:
                    print 'Error opening ChanServ settings.xml.'
                    self.channelfile = None
            elif arg == 'updates':
                try:
                    self.updatefile = argp[0]
                    open(self.updatefile, 'r').close()
                except:
                    print 'Error opening updates.txt.'
                    self.updatefile = None
            elif arg == 'proxies':
                try:
                    self.trusted_proxyfile = argp[0]
                    open(self.trusted_proxyfile, 'r').close()
                except:
                    print 'Error opening trusted proxy file.'
                    self.trusted_proxyfile = None
                    
        if self.dbtype == 'sql':
            if self.sqlurl == 'sqlite:///:memory:' or self.sqlurl == 'sqlite:///':
                print 'In-memory sqlite databases are not supported.'
                print 'Falling back to LAN mode.'
                print
                self.dbtype = 'lan'
            else:
                try:
                    sqlalchemy = __import__('sqlalchemy')
                    self.engine = sqlalchemy.create_engine(self.sqlurl, pool_recycle=300) # hopefully no thread will open more than two sql connections :/
                    if self.sqlurl.startswith('sqlite'):
                        print 'Multiple threads are not supported with sqlite, forcing a single thread'
                        print 'Please note the server performance will not be optimal'
                        print 'You might want to install a real database server or use LAN mode'
                        print
                        self.max_threads = 1
                except ImportError:
                    print 'sqlalchemy not found or invalid SQL URL, falling back to LAN mode.'
                    self.dbtype = 'lan'
        
        if self.dbtype == 'legacy':
            try:
                self.userdb = LegacyUsers.UsersHandler(self, self.engine)
                self.userdb.readAccounts()
            except:
                print traceback.format_exc()
                print 'Error loading accounts.txt database, falling back to LAN mode.'
                self.dbtype = 'lan'
        elif self.dbtype == 'sql':
            try:
                self.userdb = __import__('SQLUsers').UsersHandler
                self.userdb(self, self.engine)
            except:
                self.dbtype = 'lan'
                print traceback.format_exc()
                print 'Error importing SQL - falling back to LAN mode.'
        
        if self.dbtype == 'lan':
            self.userdb = __import__('LANUsers').UsersHandler(self)
            print 'Warning: LAN mode enabled - many user-specific features will be broken.'
        
        if self.channelfile:
            parser = LegacyChannels.Parser()
            channels = parser.parse(self.channelfile)
            
            userdb = self.getUserDB()
            for name in channels:
                channel = channels[name]
                
                owner = None
                admins = []
                
                client = userdb.clientFromUsername(channel['owner'])
                if client and client.id: owner = client.id
                
                for user in channel['admins']:
                    client = userdb.clientFromUsername(user)
                    if client and client.id:
                        admins.append(client.id)
                
                self.channels[name] = Channel(self, name, chanserv=bool(owner), owner=owner, admins=admins, key=channel['key'], antispam=channel['antispam'], topic={'user':'ChanServ', 'text':channel['topic'], 'time':int(time.time()*1000)})
            
            if self.chanserv:
                for name in channels:
                    self.chanserv.client._protocol._handle(self.chanserv.client, 'JOIN %s' % name)
        
        if not self.log:
            try:
                self.output = open('server.log', 'w')
                self.log = True
            except: pass
        
        self.parseFiles()
        
        self.protocol = Protocol(self, None)
    
    def parseFiles(self):
        if os.path.isfile('motd.txt'):
            motd = []
            f = open('motd.txt', 'r')
            data = f.read()
            f.close()
            if data:
                for line in data.split('\n'):
                    motd.append(line.strip())
            self.motd = motd
        
        if self.updatefile:
            self.updates = {}
            f = open(self.updatefile, 'r')
            data = f.read()
            f.close()
            if data:
                for line in data.split('\n'):
                    if not ':' in line: continue
                    left, right = line.split(':', 1)
                    
                    left = left.lower()
                    if ' ' in left:
                        name, version = left.rsplit(' ',1)
                    else:
                        name, version = left, 'default'
                    
                    if not name in self.updates:
                        self.updates[name] = {}
                    
                    if not version in self.updates[name]:
                        self.updates[name][version] = {}
                        
                    self.updates[name][version] = right
        
        if self.trusted_proxyfile:
            self.trusted_proxies = set([])
            f = open(self.trusted_proxyfile, 'r')
            data = f.read()
            f.close()
            if data:
                for line in data.split('\n'):
                    proxy = line.strip()
                    if not proxy.replace('.', '', 3).isdigit():
                        proxy = socket.gethostbyname(proxy)
                    
                    if proxy:
                        self.trusted_proxies.add(proxy)
    
    def getUserDB(self):
        if self.dbtype in ('legacy', 'lan'):
            return self.userdb
        elif self.dbtype == 'sql':
            return self.userdb(self, self.engine)
    
    def clientFromID(self, db_id):
        if db_id in self.db_ids: return self.db_ids[db_id]
    
    def clientFromUsername(self, username):
        if username in self.usernames: return self.usernames[username]

    def event_loop(self):
        start = time.time()
        lastsave = lastmute = lastidle = start
        while self.running:
            now = time.time()
            try:
                if now - lastsave >= 1800: # save every 30 minutes
                    lastsave = now
                    if self.dbtype == 'legacy' and self.userdb:
                        print 'Writing account database to file.',
                        start = time.time()
                        self.userdb.writeAccounts()
                        if self.channelfile:
                            writer = LegacyChannels.Writer()
                            writer.dump(self.channels, self.getUserDB().clientFromID)
                        print '..took %0.2f seconds.' % (time.time() - start)
                    
                if now - lastmute >= 1:
                    lastmute = now
                    self.mute_timeout_step()

                if now - lastidle >= 90:
                    lastidle = now
                    self.idle_timeout_step()
                
                self.console_print_step()
            except:
                self.error(traceback.format_exc())  
                
            time.sleep(max(0.1, 1 - (time.time() - start)))

    def mute_timeout_step(self):
        try:
            now = time.time()
            channels = dict(self.channels)
            for chan in channels:
                channel = channels[chan]
                mutelist = dict(channel.mutelist)
                for db_id in mutelist:
                    expiretime = mutelist[db_id]['expires']
                    if 0 < expiretime and expiretime < now:
                        del channel.mutelist[db_id]
                        channel.channelMessage('<%s> has been unmuted (mute expired).' % self.protocol.clientFromID(db_id).username)
        except:
            self.error(traceback.format_exc())

    def idle_timeout_step(self):
        now = time.time()
        for client in self.clients.values():
            if not client.logged_in and client.last_login < now - 90:
                client.Remove()

    def console_print_step(self):
        try:
            while self.console_buffer:
                line = self.console_buffer.pop(0)
                print line
                if self.log:
                    self.output.write(line+'\n')
            
            if self.output:
                self.output.flush()
        except:
            print separator
            print traceback.format_exc()
            print separator

    def error(self, error):
        error = '%s\n%s\n%s'%(separator,error,separator)
        self.console_write(error)
        for user in dict(self.usernames):
            try:
                if self.usernames[user].debug:
                    for line in error.split('\n'):
                        if line:
                            self.usernames[user].Send('SERVERMSG %s'%line)
            except KeyError: pass # the user was removed

    def console_write(self, lines=''):
        if type(lines) in(str, unicode):
            lines = lines.split('\n')
        elif not type(lines) in (list, tuple, set):
            try: lines = [lines.__repr__()]
            except: lines = ['Failed to print lines of type %s'%type(lines)]
        self.console_buffer += lines
    
    def multicast(self, clients, msg, ignore=()):
        if type(ignore) in (str, unicode): ignore = [ignore]
        static = []
        for client in clients:
            if client and not client.username in ignore:
                if client.static: static.append(client)
                else: client.Send(msg)
        
        # this is so static clients don't respond before other people even receive the message
        for client in static:
            client.Send(msg)
    
    def broadcast(self, msg, chan=None, ignore=()):
        if type(ignore) in (str, unicode): ignore = [ignore]
        try:
            if chan in self.channels:
                channel = self.channels[chan]
                if len(channel.users) > 0:
                    clients = [self.clientFromUsername(user) for user in list(channel.users)]
                    self.multicast(clients, msg, ignore)
            else:
                clients = [self.clientFromUsername(user) for user in list(self.usernames)]
                self.multicast(clients, msg, ignore)
        except: self.error(traceback.format_exc())

    def broadcast_battle(self, msg, battle_id, ignore=[]):
        if type(ignore) in (str, unicode): ignore = [ignore]
        if battle_id in self.battles:
            battle = self.battles[battle_id]
            clients = [self.clientFromUsername(user) for user in list(battle.users)]
            self.multicast(clients, msg, ignore)

    def admin_broadcast(self, msg):
        for user in dict(self.usernames):
            client = self.usernames[user]
            if 'admin' in client.accesslevels:
                client.Send('SERVERMSG Admin broadcast: %s'%msg)

    def _rebind_slow(self):
        try:
            self.parseFiles()
        except:
            self.error(traceback.format_exc())
        
        try:
            self.dispatcher.rebind()
                
            for channel in dict(self.channels): # hack, but I guess reloading is all a hack :P
                chan = self.channels[channel].copy()
                del chan['chan'] # 'cause we're passing it ourselves
                self.channels[channel] = sys.modules['Protocol'].Channel(self, channel, **chan)
            
            self.protocol = Protocol(self, None)
        except:
            self.error(traceback.format_exc())
            
        self.admin_broadcast('Done reloading.')
        self.console_write('Done reloading.')

    def reload(self):
        self.admin_broadcast('Reloading...')
        self.console_write('Reloading...')
        reload(sys.modules['SayHooks'])
        reload(sys.modules['Protocol'])
        reload(sys.modules['ChanServ'])
        reload(sys.modules['Client'])
        if 'SQLUsers' in sys.modules: reload(sys.modules['SQLUsers'])
        elif 'LANUsers' in sys.modules: reload(sys.modules['LANUsers'])
        elif 'tasserver.LegacyUsers' in sys.modules: reload(sys.modules['tasserver.LegacyUsers'])
        self.SayHooks = __import__('SayHooks')
        thread.start_new_thread(self._rebind_slow, ()) # why should reloading block the thread? :)
