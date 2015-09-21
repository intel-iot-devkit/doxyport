#!/usr/bin/env python
# Author: Mircea Bardac <mircea.bardac@intel.com>
# Copyright (c) 2015 Intel Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import os.path
import os
import shutil
import CppHeaderParser
import javalang
import argparse

class CppClassContainer():
    def __init__(self, name):
        self.name = name
        self.methods = {}
        self.properties = {}
        self.namespace_doxygen = ""
        self.class_doxygen = ""

    def add_method(self, name, m_dict):
        if name not in self.methods:
            self.methods[name] = []
        self.methods[name].append(m_dict)

    def display(self):
        print self.methods

    def param_type_list(self, params):
        p_result = []
        for p in params:
            p_result.append(p["type"])
        return p_result

    def extract_class_doxygen(self, class_content):
        namespace_doxygen = []
        class_doxygen = []
        in_namespace = True
        if not "doxygen" in class_content:
            return (namespace_doxygen, class_doxygen)
        for l in class_content["doxygen"].split("\n"):
            if in_namespace and l.find("*//*") == 0:
                namespace_doxygen.append("*/")
                l = l[2:]
                in_namespace = False
            if in_namespace:
                namespace_doxygen.append(l)
            else:
                class_doxygen.append(l)
        if in_namespace:
            class_doxygen = namespace_doxygen
            namespace_doxygen = []
        return (namespace_doxygen, class_doxygen)

    def fill(self, class_content):
        # class_content
        # ['inherits', 'line_number', 'doxygen', 'name', 'parent', 'abstract', 'namespace', 'declaration_method', 'properties', 'forward_declares', 'typedefs', 'structs', 'enums', 'final', 'nested_classes', 'methods']
        self.namespace_doxygen, self.class_doxygen = self.extract_class_doxygen(class_content)
        #print class_content["methods"]["public"]
        #print "Public methods:"
        for m in class_content["methods"]["public"]:
            #print m["doxygen"]
            #print m["rtnType"], m["const"], m["static"], m["virtual"], m["name"], m["constructor"], m["destructor"], len(m["parameters"]), param_type_list(m["parameters"])
            self.add_method(m["name"],{
                'return_type': m["rtnType"],
                'const': m["const"],
                'static': m["static"],
                'virtual': m["virtual"],
                'constructor': m["constructor"],
                'destructor': m["destructor"],
                'param_types': self.param_type_list(m["parameters"]),
                'doxygen': m.get("doxygen",None)
            })
        #print "Public properties:"
        for m in class_content["properties"]["public"]:
            #print m["doxygen"]
            #print m["rtnType"], m["const"], m["static"], m["name"]
            #print m
            self.properties[m["name"]] = {
                'type': m["type"],
                'static': m["static"],
                #'doxygen': m["doxygen"] # TODO: check if there are doxygen comments for properties
            }
        if len(class_content["methods"]["private"]) > 0:
            for m in class_content["methods"]["private"]:
                if "doxygen" in m and len(m["doxygen"]) > 0: print "*** Private method \"%s\" in class \"%s\" has doxygen comment." %(m["name"], self.name)
        if len(class_content["properties"]["private"]) > 0:
            for m in class_content["properties"]["private"]:
                if "doxygen" in m and len(m["doxygen"]) > 0: print "*** Private property \"%s\" in class \"%s\" has doxygen comment." %(m["name"], self.name)
        if len(class_content["typedefs"]["public"]) > 0:
            for m in class_content["typedefs"]["public"]:
                if "doxygen" in m and len(m["doxygen"]) > 0: print "*** Public typedef \"%s\" in class \"%s\" has doxygen comment." %(m["name"], self.name)
        if len(class_content["structs"]["public"]) > 0:
            for m in class_content["structs"]["public"]:
                if "doxygen" in m and len(m["doxygen"]) > 0: print "*** Public struct \"%s\" in class \"%s\" has doxygen comment." %(m["name"], self.name)
        if len(class_content["enums"]["public"]) > 0:
            for m in class_content["enums"]["public"]:
                if "doxygen" in m and len(m["doxygen"]) > 0: print "*** Public enum \"%s\" in class \"%s\" has doxygen comment." %(m["name"], self.name)
        if len(class_content["nested_classes"]) > 0:
            print "*** Class \"%s\" has %d public nested classes." %(self.name, len(class_content["nested_classes"]))
            #for c in class_content["nested_classes"]:
            #    print "    * %s" %(c["name"])
            #    for x in c.keys():
            #        print "      * %s: %s" %(x, c[x])

    def get_method_doxygen(self, method_name, method_declaration):
        if not method_name in self.methods: return ""
        method_list = self.methods[method_name]
        #print
        #print "!! Looking for:", method_declaration
        for cpp_m_declaration in method_list:
            #print ">>", method_name, "=", cpp_m_declaration
            if len(method_declaration["param_types"]) == len(cpp_m_declaration["param_types"]):
                if method_declaration["constructor"] != cpp_m_declaration["constructor"]: continue
                if method_declaration["destructor"] != cpp_m_declaration["destructor"]: continue
                #print "Found doxygen method:", method_name, len(cpp_m_declaration["param_types"])
                return cpp_m_declaration["doxygen"]
        return None # Not found

class JavaClassContainer:
    def add_field(self, n, d):
        self.fields[n] = d
        #print n, d

    def add_method(self, m, d):
        if m not in self.methods:
            self.methods[m] = []
        self.methods[m].append(d)
        #print "method:", m, d

    def get_type(self, type_param):
        if type_param == None: return "void"
        if type_param.name == "boolean": return "bool"
        return type_param.name

    def param_type_list(self, params):
        p_result = []
        for p in params:
            p_result.append(self.get_type(p.type))
        return p_result

    def add_field_declaration(self, declaration):
        d = {
            'type': declaration.type.name,
            'line_position': declaration._position[0],
            'private': 'private' in declaration.modifiers,
            'public': 'public' in declaration.modifiers,
            'static': 'static' in declaration.modifiers,
            'const': 'const' in declaration.modifiers,
        }
        for field in declaration.declarators:
            self.add_field(field.name, d)

    def add_constructor_declaration(self, declaration):
        d = {
            'line_position': declaration._position[0],
            'private': 'private' in declaration.modifiers,
            'protected': 'protected' in declaration.modifiers,
            'public': 'public' in declaration.modifiers,
            'static': 'static' in declaration.modifiers,
            'const': 'const' in declaration.modifiers,
            'constructor': True,
            'destructor': False,
            'return_type': "void",
            'param_types': self.param_type_list(declaration.parameters)
        }
        self.add_method(declaration.name, d)

    def add_method_declaration(self, declaration):
        d = {
            'line_position': declaration._position[0],
            'private': 'private' in declaration.modifiers,
            'protected': 'protected' in declaration.modifiers,
            'public': 'public' in declaration.modifiers,
            'static': 'static' in declaration.modifiers,
            'const': 'const' in declaration.modifiers,
            'constructor': False,
            'destructor': False,
            'return_type': self.get_type(declaration.return_type),
            'param_types': self.param_type_list(declaration.parameters)
        }
        self.add_method(declaration.name, d)

    def attach_doxygen(self, cpp_cc):
        # if cpp_cc.namespace_doxygen != "":
        #     # Merge namespace doxygen and class doxygen comments
        #     t = cpp_cc.class_doxygen
        #     cpp_cc.class_doxygen = []
        #     cpp_cc.class_doxygen.extend(cpp_cc.namespace_doxygen[:-1])
        #     if len(t) > 0:
        #         cpp_cc.class_doxygen.extend(t[1:])
        #     cpp_cc.namespace_doxygen = ""
        if self.package_line != -1 and cpp_cc.namespace_doxygen != "":
            self.doxygen_map[self.package_line] = cpp_cc.namespace_doxygen
        if self.class_line != -1 and cpp_cc.class_doxygen != "":
            self.doxygen_map[self.class_line] = cpp_cc.class_doxygen
        for method in self.methods.keys():
            method_list = self.methods[method]
            for m_declaration in method_list:
                d = cpp_cc.get_method_doxygen(method, m_declaration)
                if d == None: # Not found
                    if m_declaration["protected"]:
                        print "* Doxygen not found for method %s (possible SWIG-generated internal use code)" %(method)
                    else:
                        print "* Doxygen not found for method %s(%d params) @ line %d" %(method, len(m_declaration["param_types"]), m_declaration["line_position"])
                    d = ""
                if d != "":
                    print "* Attaching doxygen to method %s(%d params) @ line %d" %(method, len(m_declaration["param_types"]), m_declaration["line_position"])
                    self.doxygen_map[m_declaration["line_position"]] = d

    def insert_doxygen(self, out_file, doxygen_line):
        """
        insert at the current position in out_file the doxygen comment recorded
        for line doxygen_line
        """
        d = self.doxygen_map[doxygen_line]
        if type(d) == str:
            out_file.write("%s\n" %(d))
            return
        for new_line in d:
            out_file.write("%s\n" %(new_line))

    def rewrite_class_file(self):
        java_file = "%s" %(self.filename)
        orig_java_file = "%s.orig" %(self.filename)
        shutil.copyfile(java_file, orig_java_file)
        print "Rewriting %s (%d doxygen attachments).\n" %(java_file, len(self.doxygen_map))
        #print self.doxygen_map
        i = 1
        insert_lines = self.doxygen_map.keys()
        out_file = open(java_file,"wt")
        for l in open(orig_java_file).readlines():
            if i in insert_lines: self.insert_doxygen(out_file, i)
            out_file.write("%s" %(l))
            i += 1
        out_file.close()

    def __init__(self, filename, cd):
        self.filename = filename
        self.class_declaration = cd
        self.name = cd.name
        self.fields = {}
        self.methods = {}
        self.doxygen_map = {}
        self.package_line = -1
        self.class_line = -1
        c = 0
        with open(filename) as f:
            for l in f.readlines():
                c += 1
                if l.startswith("package "): self.package_line = c
                if l.startswith("public class "): self.class_line = c
        print "Class name: %s" %(self.name)
        for declaration in cd.body:
            if type(declaration) == javalang.tree.FieldDeclaration:
                self.add_field_declaration(declaration)
            if type(declaration) == javalang.tree.ConstructorDeclaration:
                self.add_constructor_declaration(declaration)
            if type(declaration) == javalang.tree.MethodDeclaration:
                self.add_method_declaration(declaration)

class SwigProcessor():
    def __init__(self, source_loc, destination_loc):
        self.cpp_classes = {}
        self.java_classes = {}
        self.source_loc = source_loc
        self.destination_loc = destination_loc
        self.parsed_destination_files = []

    def find_source(self, file_name):
        if os.path.isfile(file_name):
            return file_name
        base_file_name = os.path.basename(file_name)
        for p in self.source_loc:
            path = "%s/%s" %(p, base_file_name)
            if os.path.isfile(path):
                return path
        return None

    def find_destination(self, file_name):
        if os.path.isfile(file_name):
            return file_name
        base_file_name = os.path.basename(file_name)
        for p in self.destination_loc:
            path = "%s/%s" %(p, base_file_name)
            if os.path.isfile(path):
                return path
        return None

    def process_java(self, class_file):
        ret = {}
        print "Parsing class file: %s" %(class_file)
        tree = javalang.parse.parse(open(class_file).read())
        package_name = ""
        if tree.package is not None:
            package_name = tree.package.name
        print "Package name: %s" %(package_name)
        count = 0
        for c in tree.types:
            if type(c) == javalang.tree.ClassDeclaration:
                jc = JavaClassContainer(class_file, c)
                ret.update({jc.name: jc})
                count += 1
        if count > 1:
            print "*** Warning: Found %d Java class definitions in \"%s\"." %(count, class_file)
        return ret

    def process_header(self, root_path, header_file):
        ret = {}
        header_loc = "%s/%s" %(root_path, header_file)
        header_loc = self.find_source(header_loc)
        if header_loc == None:
            print "Unable to locate: %s" %(header_loc)
            return
        print "Processing header: %s" %(header_loc)
        try:
            parser = CppHeaderParser.CppHeader(header_loc)
        except CppHeaderParser.CppParseError as e:
            print(e)
            return ret
            #sys.exit(3)

        for class_name,class_content in parser.classes.iteritems():
            c = CppClassContainer(class_name)
            c.fill(class_content)
            #c.display()
            ret[class_name] = c
        return ret

    def process_swig(self, file_name):
        ignore_line = False
        root_path = os.path.dirname(file_name)
        for line in open(file_name).readlines():
            line = line.strip()
            if line.startswith("//"): continue
            if line.startswith("/*"): ignore_line = True
            if line.endswith("*/"):
                ignore_line = False
                continue
            if ignore_line: continue
            if line.startswith("%include"): # This is an include line
                include_file = line.split()[1].strip("\"")
                if include_file.endswith(".i"):
                    print "Ignoring recursive SWIG interface inclusions (%s)" %(include_file)
                    continue
                if include_file.endswith(".h"):
                    self.cpp_classes.update(self.process_header(root_path, include_file))
                if include_file.endswith(".hpp"):
                    self.cpp_classes.update(self.process_header(root_path, include_file))
        for class_name in self.cpp_classes.keys():
            java_file = "build/%s/%s.java" %(root_path, class_name)
            java_loc = self.find_destination(java_file)
            if java_loc == None:
                print "Unable to find Java class definition file: %s" %(java_file)
                continue
            java_file = java_loc
            orig_java_file = "%s.orig" %(java_file)
            # Restore class file from .orig file (we're rebuilding, trust backups)
            if os.path.isfile(orig_java_file):
                shutil.copyfile(orig_java_file, java_file)
            self.java_classes.update(self.process_java(java_file))
            self.parsed_destination_files.append(java_file)
        #print self.cpp_classes
        #print self.java_classes

    def push_doxygen(self):
        for class_name in self.cpp_classes.keys():
            if class_name in self.java_classes:
                #print "common class", class_name
                self.java_classes[class_name].attach_doxygen(self.cpp_classes[class_name])
                self.java_classes[class_name].rewrite_class_file()

    def append_destination_files(self, output_file_handler):
        if output_file_handler == None: return
        for l in self.parsed_destination_files:
            output_file_handler.write("%s\n" %(l))

parser = argparse.ArgumentParser()
parser.add_argument("file_list", help = "List with SWIG interface files")
parser.add_argument("-s","--source", default = "", help = "One or more paths where to look for C/C++ headers")
parser.add_argument("-d","--destination", default = "", help = "One or more paths where to look for Java class definitions")
parser.add_argument("-o","--output", help = "Write a file with the list of parsed files")
args = parser.parse_args()

swig_list_file = args.file_list
if not os.path.isfile(swig_list_file):
    print "File not found: %s" %(swig_list_file)
    sys.exit(2)

output_file_handler = None
if args.output != None:
    try:
        output_file_handler = open(args.output,"wt")
    except:
        pass

for swig_file in open(swig_list_file).readlines():
    swig_file = swig_file.strip()
    sp = SwigProcessor(args.source.split(","),args.destination.split(","))
    sp.process_swig(swig_file)
    sp.push_doxygen()
    sp.append_destination_files(output_file_handler)

if output_file_handler != None:
    output_file_handler.close()
