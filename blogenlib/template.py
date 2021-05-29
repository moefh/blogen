
import re
import os.path

def replace_vars(txt, data):
    def repl_data(match):
        var = match.group(1)
        if var in data:
            return data[var]
        return ''
    
    def repl_if(match):
        var = match.group(1)
        text_if_true  = match.group(2)
        text_if_false = match.group(3)
        if (var in data) and data[var]:
            return text_if_true
        else:
            return text_if_false
        
    txt = re.sub(r'\$if\{([a-z0-9_]+):([^:\}]*):([^:\}]*)\}', repl_if, txt)
    txt = re.sub(r'\$\{([a-z0-9_]+)\}', repl_data, txt)
    return txt

class Element:

    def build_elements(collector, els, data):
        for el in els:
            if isinstance(el, str):
                collector.append(replace_vars(el, data))
            else:
                el.build(collector, data)
    
    def __init__(self, name, line):
        self.name = name
        self.line = line
        self.children = []

    def add_child(self, child):
        #if (len(self.children) > 0) and isinstance(child, str) and isinstance(self.children[-1], str):
        #    self.children[-1] = self.children[-1] + '\n' + child
        #else:
        self.children.append(child)

    def build(self, collector, data):
        Element.build_elements(collector, self.children, data)

class DocumentElement(Element):

    def __init__(self):
        Element.__init__(self, '*document*', 0)

class IncludeElement(Element):

    def __init__(self, line, tpl_name, tpl_proc):
        Element.__init__(self, 'include', line)
        self.tpl_name = tpl_name
        self.tpl_proc = tpl_proc

    def build(self, collector, data):
        collector.append(self.tpl_proc.build(self.tpl_name, data))
    
class ForeachElement(Element):

    def __init__(self, line, var):
        Element.__init__(self, 'foreach', line);
        self.var = var

    def build(self, collector, data):
        if (self.var not in data) or (not isinstance(data[self.var], list)):
            return
        for item in data[self.var]:
            sub_data = data.copy()
            sub_data.update(item)
            Element.build(self, collector, sub_data)

class IfElementCondition:

    def __init__(self, test):
        self.test = test
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def run_test(self, data):
        return (self.test in data) and (data[self.test])
        
class IfElement(Element):

    def __init__(self, line, cond):
        Element.__init__(self, 'if', line);
        self.conds = []
        self.add_cond(cond)

    def add_cond(self, cond):
        self.conds.append(IfElementCondition(cond))

    def add_child(self, child):
        if len(self.conds) == 0:
            raise Exception('trying to add child to an if with no conditions!')
        Element.add_child(self, child)
        self.conds[-1].add_child(child)

    def build(self, collector, data):
        for cond in self.conds:
            if cond.run_test(data):
                Element.build_elements(collector, cond.children, data)
                return

class TemplateProcessor:

    def __init__(self, tpl_dir):
        self.tpl_dir = tpl_dir
        self.cache = {}

    def read_tpl(self, name):
        if name in self.cache:
            return self.cache[name]
        filename = os.path.join(self.tpl_dir, name + '.tpl')
        with open(filename, 'r') as f:
            self.cache[name] = f.read()
        return self.cache[name]

    def build(self, tpl_name, data):
        txt = self.read_tpl(tpl_name)

        # if there are no loops or ifs, just replace vars on the whole thing
        if '%{' not in txt:
            return replace_vars(txt, data)

        lines = txt.split('\n')
        doc = DocumentElement()
        stack = [ doc ]
        for line_num, line in enumerate(lines):
            # %{include NAME}
            match = re.fullmatch(r'\s*\%\{\s*include\s+"(.*)"\s*\}\s*', line)
            if match:
                tpl_name = match.group(1)
                stack[-1].add_child(IncludeElement(line_num, tpl_name, self))
                continue
            
            # %{foreach NAME}
            match = re.fullmatch(r'\s*\%\{\s*foreach\s+([a-z0-9_]+)\s*\}\s*', line)
            if match:
                var = match.group(1)
                el = ForeachElement(line_num, var)
                stack[-1].add_child(el)
                stack.append(el)
                continue

            # %{if CONDITION}
            match = re.fullmatch(r'\s*\%\{\s*if\s+(.*)\s*\}\s*', line)
            if match:
                cond = match.group(1)
                el = IfElement(line_num, cond)
                stack[-1].add_child(el)
                stack.append(el)
                continue

            # %{elif CONDITION}
            match = re.fullmatch(r'\s*\%\{\s*elif\s+(.*)\s*\}\s*', line)
            if match:
                cond = match.group(1)
                if not isinstance(stack[-1], IfElement):
                    raise Exception('invalid %{elif} at line {}'.format(line_num+1))
                stack[-1].add_cond(cond)
                continue

            # %{end}
            match = re.fullmatch(r'\s*\%\{\s*end\s*\}\s*', line)
            if match:
                if len(stack) <= 1:
                    raise Exception('invalid %{end} at line {}'.format(line_num+1))
                stack.pop()
                continue

            # text line
            stack[-1].add_child(line)
                

        if len(stack) > 1:
            raise Exception("unterminated %{" + stack[-1].name + "} in line " + str(stack[-1].line+1))

        ret = []
        doc.build(ret, data)
        return '\n'.join(ret)
    
