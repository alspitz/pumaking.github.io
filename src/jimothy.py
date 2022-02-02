import os

import spec
from util import getf

CMD_OPEN = "{{"
CMD_CLOSE = "}}"

class Result:
  def __init__(self, text, n_cmds):
    self.text = text
    self.n_cmds = n_cmds

def include(fn):
  return f"{CMD_OPEN} {fn} {CMD_CLOSE}"

def cmd_include_html(src_path, cmd, context):
  return getf(src_path/cmd).rstrip()

def cmd_blog_latest(src_path, cmd, context):
  context['blog'] = spec.blog_entries[0]
  return include("blog_entry_template.html")

def cmd_blog_body(src_path, cmd, context):
  return include("blog/%s.html" % context['blog'].srcfn)

def cmd_for(src_path, cmd, context):
  forw, varname, inw, listw, itertext = cmd.split(None, 4)
  assert forw == "for"
  if inw != "in":
    print("\n\tERROR: Invalid for syntax. Use \"in\"")
    return None

  if not hasattr(spec, listw):
    print("\n\tERROR: object \"%s\" not found" % listw)
    return None

  text = ""
  listo = getattr(spec, listw)
  for obj in listo:
    text += itertext.format(**{**context, varname : obj})

  return text.strip()

def cmd_headerlink_class(src_path, cmd, context):
  rest = cmd.removeprefix("headerlink-class").strip()
  cls = "headerlink"
  if rest and rest in context['filename'].stem:
    cls += " headerlinkcurrent"

  return cls

def make_blogs(src_path, blogs, out_path):
  for blog in blogs:
    blogfn = "%s.html" % blog.srcfn
    res = process_sourcefile(src_path/"blog_page_template.html", dict(blog=blog))
    write_file(out_path/"blog"/blogfn, res)

cmdmap = {
  'blog-latest' : cmd_blog_latest,
  'blog-body'   : cmd_blog_body,
  'headerlink-class' : cmd_headerlink_class,
  #'blog-links'  cmd_blog_links,
}

def process_sourcefile(filename, context=None, debug=False):
  print("%s %s" %  (filename, context), end='... ')
  text = getf(filename)
  if context is None:
    context = dict()

  context.update(filename=filename)

  n_cmds = 0
  cmdstart = 0
  while 1:
    cmdstart = text.find(CMD_OPEN, cmdstart)
    cmdend = text.find(CMD_CLOSE, cmdstart)
    if cmdend < 0:
      break

    # Seems bad and hacky. Let's see if it will last...
    # Done so that html templates don't have to escape curly brackets.
    # The choice {{ <cmd> }} for templates clashes with Python's str.format because
    # "{{ text }}".format() returns "{ text }".
    use_format = False
    # Newlines are useful for for loops. Only remove spaces and tabs.
    fullcmd = text[cmdstart : cmdend].removeprefix(CMD_OPEN).strip(' \t')
    if debug:
      print("\n\tProcessing cmd", fullcmd)
      input()
    n_cmds += 1

    cmdwords = fullcmd.split()
    cmd = cmdwords[0]

    if fullcmd.endswith('.html'):
      includetext = cmd_include_html(src_path, fullcmd, context)
    elif cmd in cmdmap:
      includetext = cmdmap[cmd](src_path, fullcmd, context)
    elif cmd in spec.varmap:
      includetext = spec.varmap[cmd]
      use_format = True
    elif cmd == 'for':
      includetext = cmd_for(src_path, fullcmd, context)
    else:
      print("\n\tERROR: Unhandled jimothy command %s" % fullcmd)
      cmdstart = cmdend + len(CMD_CLOSE)
      continue

    if includetext is None:
      print("\n\tERROR: Cmd \"%s\" failed." % fullcmd)
      continue

    if use_format:
      includetext = includetext.format(**context)

    text = text[:cmdstart] + includetext + text[cmdend + len(CMD_CLOSE):]
    if debug:
      print(text[cmdstart:cmdstart + 20])

  return Result(text, n_cmds)

def write_file(outfile, res):
  write_file = True
  if outfile.exists():
    oldout = getf(outfile)
    if oldout == res.text:
      print("same")
      write_file = False

  if write_file:
    print("write to %s (%d macros). Press Enter to continue" % (outfile, res.n_cmds))
    input()
    with open(outfile, "w") as f:
      f.write(res.text)

def process(path, files, out_path):
  fs = os.listdir(path)

  for fname in os.listdir(path):
    if fname not in files:
      continue

    res = process_sourcefile(path/fname)
    write_file(out_path/fname, res)

if __name__ == "__main__":
  from pathlib import Path

  src_path = Path(__file__).resolve().parent
  root_path = src_path.parent
  out_path = root_path.parent / "alspitz-deploy"

  process(root_path, spec.root_files, out_path)
  process(src_path, spec.source_files, out_path)
  make_blogs(src_path, spec.blog_entries, out_path)
