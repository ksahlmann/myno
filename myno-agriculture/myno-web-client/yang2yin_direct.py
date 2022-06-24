#!/usr/bin/python

#this file has been created primarily from pyang's __init__.py and its yin.py

#pyang doesn't include a function for direct calling from within python
#so direct_yang2yin_call() takes care of that.

import sys
import os
import optparse
import re
import io

if sys.version < '3':
    import codecs

import pyang
from pyang import plugin
from pyang import error
from pyang import util
from pyang import hello
from pyang import statements
from pyang import syntax
import pyang.repository
import pyang.context

from xml.sax.saxutils import quoteattr
from xml.sax.saxutils import escape


yin_string=''


def direct_yang2yin_call(text_to_parse):
	return init_ctx(text_to_parse)
	
def init_ctx(text_to_parse):
    exit_code = 0
    modules = []
    filenames = []
    
    r = re.compile(r"^(.*?)(\@(\d{4}-\d{2}-\d{2}))?\.(yang|yin)$")

    usage = """%prog [options] [<filename>...]

    Validates the YANG module in <filename> (or stdin), and all its dependencies."""

    plugindirs = []
    # check for --plugindir
    idx = 1
    while '--plugindir' in sys.argv[idx:]:
        idx = idx + sys.argv[idx:].index('--plugindir')
        plugindirs.append(sys.argv[idx + 1])
        idx = idx + 1
    plugin.init(plugindirs)

    fmts = {}
    for p in plugin.plugins:
        p.add_output_format(fmts)
        
    path = ''
    repos = pyang.repository.FileRepository(path, no_path_recurse=None)

    ctx = pyang.context.Context(repos)
    
    emit_obj = fmts["yin"]
    emit_obj.setup_fmt(ctx)
    
    if len(filenames) == 0:
        text = text_to_parse
        module = ctx.add_module('<stdin>', text)
        if module is None:
            exit_code = 1
        else:
            modules.append(module)
	
    modulenames = []
    for m in modules:
        modulenames.append(m.arg)
        for s in m.search('include'):
            modulenames.append(s.arg)

    opts =       {'verbose': None, 'list_errors': None, 'print_error_code': None, 'warnings': [], 'errors': [], 'ignore_error_tags': [], 'ignore_errors': None, 'canonical': None, 'max_line_len': None, 'max_identifier_len': None, 'outfile': None, 'features': [], 'max_status': None, 'deviations': [], 'path': [], 'plugindir': None, 'strict': None, 'lax_quote_checks': None, 'lax_xpath_checks': None, 'trim_yin': None, 'hello': None, 'keep_comments': None, 'no_path_recurse': None, 'ensure_hyphenated_names': None, 'format': 'yin', 'yang_canonical': None, 'yang_remove_unused_imports': None, 'yin_canonical': None, 'yin_pretty_strings': None, 'dsdl_no_documentation': False, 'dsdl_no_dublin_core': False, 'dsdl_record_defs': False, 'dsdl_lax_yang_version': False, 'bbf': None, 'capa_entity': False, 'check_update_from': None, 'old_path': [], 'depend_target': None, 'depend_no_submodules': None, 'depend_from_submodules': None, 'depend_recurse': None, 'depend_extension': None, 'depend_include_path': None, 'depend_ignore': [], 'ieee': None, 'ietf': None, 'jstree_no_path': None, 'jstree_path': None, 'lint': None, 'lint_namespace_prefixes': [], 'lint_modulename_prefixes': [], 'mef': None, 'print_revision': None, 'omni_tree_path': None, 'doctype': 'data', 'sample_defaults': False, 'sample_annots': False, 'sample_path': None, 'tree_help': None, 'tree_depth': None, 'tree_line_length': None, 'tree_path': None, 'tree_print_groupings': None, 'tree_print_yang_data': None, 'uml_classes_only': False, 'uml_pages_layout': None, 'uml_outputdir': None, 'uml_title': None, 'uml_header': None, 'uml_footer': None, 'uml_longids': False, 'uml_inline': False, 'uml_inline_augments': False, 'uml_descr': False, 'uml_no': '', 'uml_truncate': '', 'uml_max_enums': '3', 'uml_gen_filter_file': False, 'uml_filter_file': None}
    opts = dotdict(opts) 
    
    ctx.opts = opts
    ctx.opts.yin_canonical=None

    for filename in ctx.opts.deviations:
        try:
            fd = io.open(filename, "r", encoding="utf-8")
            text = fd.read()
        except IOError as ex:
            sys.stderr.write("error %s: %s\n" % (filename, str(ex)))
            sys.exit(1)
        except UnicodeDecodeError as ex:
            s = str(ex).replace('utf-8', 'utf8')
            sys.stderr.write("%s: unicode error: %s\n" % (filename, s))
            sys.exit(1)
        m = ctx.add_module(filename, text)
        if m is not None:
            ctx.deviation_modules.append(m)
    
    for p in plugin.plugins:
        p.pre_validate_ctx(ctx, modules)

    if emit_obj is not None and len(modules) > 0:
        emit_obj.pre_validate(ctx, modules)

    ctx.validate()

    # verify the given features
    for m in modules:
        if m.arg in ctx.features:
            for f in ctx.features[m.arg]:
                if f not in m.i_features:
                    sys.stderr.write("unknown feature %s in module %s\n" %
                                     (f, m.arg))
                    sys.exit(1)

    if emit_obj is not None and len(modules) > 0:
        emit_obj.post_validate(ctx, modules)

    final_output=""

    if emit_obj is not None and len(modules) > 0:
        print("not none")
        tmpfile = None
        if (1==1):#o.outfile == None:
            if sys.version < '3':
                fd = codecs.getwriter('utf8')(sys.stdout)
            else:
                fd = sys.stdout
        else:
            tmpfile = o.outfile + ".tmp"
            if sys.version < '3':
                fd = codecs.open(tmpfile, "w+", encoding="utf-8")
            else:
                fd = io.open(tmpfile, "w+", encoding="utf-8")
        try:
            print("--")
            global yin_string
            yin_string=''
            emit_yin(ctx, modules[0], final_output)
        except error.EmitError as e:
            if e.msg != "":
                sys.stderr.write(e.msg + '\n')
            if tmpfile != None:
                fd.close()
                os.remove(tmpfile)
            sys.exit(e.exit_code)
        except:
            if tmpfile != None:
                fd.close()
                os.remove(tmpfile)
            raise
        if tmpfile != None:
            fd.close()
            os.rename(tmpfile, o.outfile)
	
    return yin_string
    sys.exit(exit_code)

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def emit_yin(ctx, module, fd):
    global yin_string
    yin_namespace = "urn:ietf:params:xml:ns:yang:yin:1"

    yin_string+=('<?xml version="1.0" encoding="UTF-8"?>\n')
    yin_string+=('<%s name="%s"\n' % (module.keyword, module.arg))
    yin_string+=(' ' * len(module.keyword) + '  xmlns="%s"' % yin_namespace)

    prefix = module.search_one('prefix')
    if prefix is not None:
        namespace = module.search_one('namespace')
        yin_string+=('\n')
        yin_string+=(' ' * len(module.keyword))
        yin_string+=('  xmlns:' + prefix.arg + '=' +
                 quoteattr(namespace.arg))
    else:
        belongs_to = module.search_one('belongs-to')
        if belongs_to is not None:
            prefix = belongs_to.search_one('prefix')
            if prefix is not None:
                # read the parent module in order to find the namespace uri
                res = ctx.read_module(belongs_to.arg, extra={'no_include':True})
                if res is not None:
                    namespace = res.search_one('namespace')
                    if namespace is None or namespace.arg is None:
                        pass
                    else:
                        # success - namespace found
                        yin_string+=('\n')
                        yin_string+=(' ' * len(module.keyword))
                        yin_string+=('  xmlns:' + prefix.arg + '=' +
                                 quoteattr(namespace.arg))
            
    for imp in module.search('import'):
        prefix = imp.search_one('prefix')
        if prefix is not None:
            rev = None
            r = imp.search_one('revision-date')
            if r is not None:
                rev = r.arg
            mod = statements.modulename_to_module(module, imp.arg, rev)
            if mod is not None:
                ns = mod.search_one('namespace')
                if ns is not None:
                    yin_string+=('\n')
                    yin_string+=(' ' * len(module.keyword))
                    yin_string+=('  xmlns:' + prefix.arg + '=' +
                             quoteattr(ns.arg))
    yin_string+=('>\n')
    if ctx.opts.yin_canonical:
        substmts = grammar.sort_canonical(module.keyword, module.substmts)
    else:
        substmts = module.substmts
    for s in substmts:
        emit_stmt(ctx, module, s, fd, '  ', '  ')
    yin_string+=('</%s>\n' % module.keyword)
    
    
def emit_stmt(ctx, module, stmt, fd, indent, indentstep):
    global yin_string
    if util.is_prefixed(stmt.raw_keyword):
        # this is an extension.  need to find its definition
        (prefix, identifier) = stmt.raw_keyword
        tag = prefix + ':' + identifier
        if stmt.i_extension is not None:
            ext_arg = stmt.i_extension.search_one('argument')
            if ext_arg is not None:
                yin_element = ext_arg.search_one('yin-element')
                if yin_element is not None and yin_element.arg == 'true':
                    argname = prefix + ':' + ext_arg.arg
                    argiselem = True
                else:
                    # explicit false or no yin-element given
                    argname = ext_arg.arg
                    argiselem = False
            else:
                argiselem = False
                argname = None
        else:
            argiselem = False
            argname = None
    else:
        (argname, argiselem) = syntax.yin_map[stmt.raw_keyword]
        tag = stmt.raw_keyword
    if argiselem == False or argname is None:
        if argname is None:
            attr = ''
        else:
            attr = ' ' + argname + '=' + quoteattr(stmt.arg)
        if len(stmt.substmts) == 0:
            yin_string+=(indent + '<' + tag + attr + '/>\n')
        else:
            yin_string+=(indent + '<' + tag + attr + '>\n')
            for s in stmt.substmts:
                emit_stmt(ctx, module, s, fd, indent + indentstep,
                          indentstep)
            yin_string+=(indent + '</' + tag + '>\n')
    else:
        yin_string+=(indent + '<' + tag + '>\n')
        if ctx.opts.yin_pretty_strings:
            # since whitespace is significant in XML, the current
            # code is strictly speaking incorrect.  But w/o the whitespace,
            # it looks too ugly.
            yin_string+=(indent + indentstep + '<' + argname + '>\n')
            yin_string+=(fmt_text(indent + indentstep + indentstep, stmt.arg))
            yin_string+=('\n' + indent + indentstep + '</' + argname + '>\n')
        else:
            yin_string+=(indent + indentstep + '<' + argname + '>' + \
                       escape(stmt.arg) + \
                       '</' + argname + '>\n')
        if ctx.opts.yin_canonical:
            substmts = grammar.sort_canonical(stmt.keyword, stmt.substmts)
        else:
            substmts = stmt.substmts
        for s in substmts:
            emit_stmt(ctx, module, s, fd, indent + indentstep, indentstep)
        yin_string+=(indent + '</' + tag + '>\n')

    

