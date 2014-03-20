import sublime
import sublime_plugin
import os
import subprocess
import re
import time

settingsfile = 'Enhanced-R.sublime-settings'

# escape double quote
def escape_dq(string):
    string = string.replace('\\', '\\\\')
    string = string.replace('"', '\\"')
    return string

# get platform specific key
def platform_setting(key, default=None):
    plat = sublime.platform()
    settings = sublime.load_settings(settingsfile)
    plat_settings = settings.get(plat)
    if key in plat_settings:
        return plat_settings[key]
    else:
        return default

# the main function
class RSendTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, cmd):

        # clean command before sending to R
        cmd = cmd.rstrip('\n')
        if len(re.findall("\n", cmd)) == 0:
            cmd = cmd.lstrip()

        App = platform_setting("App")
        if App == "SublimeREPL":
            external_id = self.view.scope_name(0).split(" ")[0].split(".", 1)[1]
            self.view.window().run_command("repl_send", {"external_id": external_id, "text": cmd})
            return

        plat = sublime.platform()
        if plat == 'osx':
            App = platform_setting("App", "R")

            if App == "RStudio":
                args = ['osascript']
                apple_script = ('tell application "RStudio" to activate\n'
                                'delay 0.25\n'
                                'tell application "System Events"\n'
                                    'keystroke "v" using {command down}\n'
                                    'keystroke return\n'
                                'end tell\n'
                                'tell application "Sublime Text" to activate\n')
                args.extend(['-e', apple_script])
                # print(args[2])
                oldcb = sublime.get_clipboard()
                sublime.set_clipboard(cmd)
                proc = subprocess.Popen(args)
                # time.sleep(1)
                # sublime.set_clipboard(oldcb)

            cmd = escape_dq(cmd)
            if re.match('R[0-9]*$', App):
                args = ['osascript']
                args.extend(['-e', 'tell app "' + App + '" to cmd "' + cmd + '"'])
                subprocess.Popen(args)
            elif App == 'Terminal':
                args = ['osascript']
                args.extend(['-e', 'tell app "Terminal" to do script "' + cmd + '" in front window\n'])
                subprocess.Popen(args)
            elif re.match('iTerm', App):
                    # when cmd ends in a space, iterm does not execute. Thus append a line break.
                    if (cmd[-1:] == ' '):
                        cmd += '\n'
                    args = ['osascript']
                    apple_script = ('tell application "' + App + '"\n'
                                        'tell the first terminal\n'
                                            'tell current session\n'
                                                'write text "' + cmd + '"\n'
                                            'end tell\n'
                                        'end tell\n'
                                    'end tell\n')
                    args.extend(['-e', apple_script])
                    subprocess.Popen(args)

        elif plat == 'windows':
            App = platform_setting("App", "R64")
            progpath = platform_setting(App, str(1) if App == "R64" else str(0))
            ahk_path = os.path.join(sublime.packages_path(), 'Enhanced-R', 'bin','AutoHotkeyU32')
            ahk_script_path = os.path.join(sublime.packages_path(), 'Enhanced-R', 'bin','Rgui.ahk')
            # manually add "\n" to keep the indentation of first line of block code,
            # "\n" is later removed in AutoHotkey script
            cmd = "\n"+cmd

            args = [ahk_path, ahk_script_path, progpath, cmd ]
            subprocess.Popen(args)

        elif plat == 'linux':
            App = platform_setting("App", "tmux")
            if App == "tmux":
                progpath = platform_setting("tmux", "tmux")
                subprocess.call([progpath, 'set-buffer', cmd + "\n"])
                subprocess.call([progpath, 'paste-buffer', '-d'])

            elif App == "screen":
                progpath = platform_setting("screen", "screen")
                subprocess.call([progpath, '-X', 'stuff', cmd + "\n"])


class RSendSelectCommand(sublime_plugin.TextCommand):

    # expand selection to {...} when being triggered
    def expand_sel(self, sel):
        esel = self.view.find(r"""^.*(\{(?:(["\'])(?:[^\\]|\\.)*?\2|#.*$|[^\{\}]|(?1))*\}).*$"""
            , self.view.line(sel).begin())
        if self.view.line(sel).begin() == esel.begin():
            return esel

    def run(self, edit):
        view = self.view
        cmd = ''
        for sel in [s for s in view.sel()]:
            if sel.empty():
                thiscmd = view.substr(view.line(sel))
                line = view.rowcol(sel.end())[0]
                # if the line ends with {, expand to {...}
                if re.match(r".*\{\s*$", thiscmd):
                    esel = self.expand_sel(sel)
                    if esel:
                        thiscmd = view.substr(esel)
                        line = view.rowcol(esel.end())[0]
                if view.settings().get("r_auto_advance", False):
                    view.sel().subtract(sel)
                    pt = view.text_point(line+1,0)
                    view.sel().add(sublime.Region(pt,pt))
            else:
                thiscmd = view.substr(sel)
            cmd += thiscmd +'\n'

        view.run_command("r_send_text", {"cmd": cmd})

class RChangeDirCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        fname = self.view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return
        dirname = os.path.dirname(fname)
        cmd = "setwd(\"" + escape_dq(dirname) + "\")"
        self.view.run_command("r_send_text", {"cmd": cmd})

class RSourceCodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        fname = self.view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return
        cmd = "source(\"" +  escape_dq(fname) + "\")"
        self.view.run_command("r_send_text", {"cmd": cmd})

class RGetHelpCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            if region.begin() == region.end():
                word = self.view.word(region)
            else:
                word = region
            if not word.empty():
                keyword = self.view.substr(word)

        cmd = "?" + keyword
        self.view.run_command("r_send_text", {"cmd": cmd})