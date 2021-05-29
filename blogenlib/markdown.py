
import re

class Element:

    html_quote_map = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
    }

    def __init__(self, children = None):
        self.children = []
        if children:
            self.add_children(children)

    def add_child(self, el):
        self.children.append(el)

    def add_children(self, els):
        self.children.extend(els)

    def is_block(self):
        return False

    def element_contains_block(el):
        if not isinstance(el, Element):
            return False
        if el.is_block():
            return True
        for child in el.children:
            if Element.element_contains_block(child):
                return True
        return False
    
    def render_list(els, renderer = None):
        ret = []
        for el in els:
            ret.append(Element.render_element(el, renderer))
        return ret
        
    def render_element(el, renderer = None):
        if isinstance(el, Element):
            return el.render(renderer)
        return el

    def quote_html(text):
        return "".join(Element.html_quote_map.get(c, c) for c in text)
    
    def slashed_char(ch):
        if ch == '\\': return ch
        if ch == '\'': return ch
        if ch == '\"': return ch
        if ch == 'n': return '\n'
        if ch == 'r': return '\r'
        if ch == 't': return '\t'
        return ch
    
    def apply_slashes(text):
        pos = 0
        ret = []
        while pos < len(text):
            c = text[pos]
            pos += 1
            if (c == '\\') and (pos < len(text)):
                ret.append(Element.slashed_char(text[pos]))
                pos += 1
            else:
                ret.append(c)
        return ''.join(ret)

class CommandElement(Element):

    def __init__(self, text):
        Element.__init__(self)
        self.command = text.strip()

    def render(self, renderer = None):
        if renderer:
            return renderer.process_command(self.command)
        return '<!-- markdown command: "' + Element.quote_html(self.command) + '" -->'
    
class HeaderElement(Element):

    def __init__(self, text):
        Element.__init__(self)
        match = re.fullmatch(r'(#+)\s*([^#].*)', text)
        if match:
            self.level = len(match.group(1))
            self.text = match.group(2)
        else:
            self.level = 0
            self.text = text

    def render(self, renderer = None):
        return ('<p class="header-{}">'.format(self.level) +
                self.text +
                '</p>')

    def is_block(self):
        return True

class TableElement(Element):

    def __init__(self, text, parser):
        Element.__init__(self)
        self.parse_table(text, parser)

    def parse_table(self, text, parser):
        lines = text.split('\n')
        self.align = []
        self.rows = []
        for line in lines:
            row = line.split('|')[1:-1]
            if '---' in row[0]:
                for cell in row:
                    spec = cell.strip()
                    left_align  = cell.startswith(':')
                    right_align = cell.endswith(':')
                    if left_align and right_align: self.align.append('center')
                    elif left_align:               self.align.append('left')
                    elif right_align:              self.align.append('right')
                    else:                          self.align.append('left')
            else:
                row_els = []
                for cell in row:
                    els = parser.parse_text(cell.strip())
                    if (len(els) == 0) or isinstance(els[0], Element) or not re.fullmatch(r'<!--\s*-->', els[0]):
                        row_els.append(els)
                self.rows.append(row_els)

    def get_col_align(self, col_num):
        if self.align and (col_num < len(self.align)):
            return self.align[col_num]
        return 'left'

    def is_row_empty(self, row):
        for cell in row:
            if len(cell) > 0:
                return False
        return True
    
    def render_row(self, ret, row, renderer, cell_tag):
        ret.append('<tr>\n')
        for col_num, cell in enumerate(row):
            align = self.get_col_align(col_num)
            if align:
                ret.append('<{} align="{}">'.format(cell_tag, align))
            else:
                ret.append('<{}>'.format(cell_tag))
            for txt in Element.render_list(cell, renderer):
                ret.append(txt)
            ret.append('</{}>'.format(cell_tag))
        ret.append('</tr>\n')

    def render(self, renderer = None):
        ret = []
        ret.append('<div class="table-wrapper"><div class="table-scroll">\n')
        ret.append('<table>\n')

        if not self.is_row_empty(self.rows[0]):
            self.render_row(ret, self.rows[0], renderer, 'th')
        for row in self.rows[1:]:
            self.render_row(ret, row, renderer, 'td')
        ret.append('</table>')
        ret.append('</div></div>\n')
        return ''.join(ret)

    def is_block(self):
        return True

class ListElement(Element):
    def __init__(self, items):
        Element.__init__(self)
        self.items = items

    def render(self, renderer = None):
        #return '<pre style="overflow: auto">{}</pre>'.format(self.text)
        ret = []
        ret.append('<ul>')
        for item in self.items:
            ret.append('  <li>{}</li>'.format(''.join(Element.render_list(item, renderer))))
        ret.append('</ul>')
        return '\n'.join(ret)

    def is_block(self):
        return True
    
class ImageElement(Element):

    def __init__(self, url, alt):
        Element.__init__(self, alt)
        self.url = url
        self.alt = alt

    def render(self, renderer = None):
        info = renderer.get_image_info(self.url);
        alt_one_line = self.alt.replace('\n', ' ')
        if ('width' in info) and ('height' in info):
            img_tag = '<img width="{}" height="{}" src="{}" alt="{}" title="{}">'.format(info['width'], info['height'], info['url'], alt_one_line, alt_one_line)
        else:
            img_tag = '<img src="{}" alt="{}" title="{}">'.format(info['url'], alt_one_line, alt_one_line)
            
        return ('<div class="image">\n  ' +
                img_tag +
                '\n  <div class="image-caption">{}</div>\n'.format(alt_one_line) +
                '</div>')

    def is_block(self):
        return True

class LinkElement(Element):

    def __init__(self, url, children):
        Element.__init__(self, children)
        self.url = url

    def render(self, renderer = None):
        return ('<a href="{}">'.format(self.url) +
                ''.join(Element.render_list(self.children, renderer)) +
                '</a>')

class TextFormatElement(Element):

    def __init__(self, fmt, children):
        Element.__init__(self, children)
        if fmt == '**':
            self.tag = 'i'
        elif fmt == '*':
            self.tag = 'b'
        else:
            self.tag = 'span'

    def render(self, renderer = None):
        return ('<{}>'.format(self.tag) +
                ''.join(Element.render_list(self.children, renderer)) +
                '</{}>'.format(self.tag))

class CodeElement(Element):

    def __init__(self, text):
        Element.__init__(self)
        self.text = text

    def render(self, renderer = None):
        return '<code>{}</code>'.format(self.text)

class MultilineCodeElement(Element):

    def __init__(self, text):
        Element.__init__(self)
        self.lines = text.split('\n')
        while len(self.lines) < 2:
            self.lines.append('')
        parts = re.split(r'\s+', self.lines[0], maxsplit = 1)
        self.code_type = parts[0]
        self.header = parts[1] if len(parts) > 1 else ''

    def render_line(self, num, line):
        return '<span class="line-num">{:3}     </span>{}'.format(num, line)
        
    def render(self, renderer = None):
        header = '<div class="multiline-code-header">{}</div>\n'.format(self.header) if len(self.header) > 0 else ''
            
        return (header +
                '<div class="multiline-code-wrapper">\n' +
                '<div class="multiline-code">\n<pre>' +
                #'\n'.join([ self.render_line(num, line) for num, line in enumerate(self.lines[1:]) ]) +
                '\n'.join(self.lines[1:]) +
                '</pre>\n</div>\n</div>')

    def is_block(self):
        return True

class ParagraphElement(Element):

    def __init__(self):
        Element.__init__(self)

    def render(self, renderer = None):
        if (len(self.children) == 1) and (isinstance(self.children[0], Element)) and (self.children[0].is_block()):
            return self.children[0].render(renderer)
        
        rendered_content = ''.join(Element.render_list(self.children, renderer))
        for child in self.children:
            if Element.element_contains_block(child):
                return '<div>\n' + rendered_content + '\n</div>'
        return '<p>\n' + rendered_content + '\n</p>'

class Markdown:

    def __init__(self):
        self.blocks = []

    def get_elements(self, from_class):
        def sweep_tree(node, ret):
            if isinstance(node, from_class):
                ret.append(node)
            for child in node.children:
                if isinstance(child, Element):
                    sweep_tree(child, ret)
                
        ret = []
        for block in self.blocks:
            sweep_tree(block, ret)
        return ret
            
    def add_block(self, el):
        self.blocks.append(el)
        
    def render(self, renderer = None):
        l = []
        for block in self.blocks:
            l.append(block.render(renderer))
        return '\n\n'.join(l)

class Parser:
    
    def parse(self, text):
        markdown = Markdown()
        pos = 0
        while pos < len(text):
            para = ParagraphElement()
            while (pos < len(text)) and (text[pos].isspace()):
                pos += 1
            if text[pos:pos+3] == '```':
                end_pos = text.find('```', pos+3)
                para.add_child(MultilineCodeElement(text[pos+3:end_pos]))
                pos = end_pos + 3
            else:
                end_pos = text.find('\n\n', pos)
                if end_pos < 0:
                    end_pos = len(text)
                para.add_children(self.parse_text(text[pos:end_pos]))
                pos = end_pos
            markdown.add_block(para)
        return markdown

    def parse_text(self, text):
        ret = []
        pos = 0
        start_pos = 0
        while pos < len(text):
            if text[pos] in '{}[]!#%|`-*':
                (new_pos, el) = self.parse_special(text, pos)
                if el is not None:
                    if start_pos < pos:
                        ret.append(text[start_pos:pos])
                    ret.append(el)
                    pos = new_pos - 1  # we'll add 1 soon
                    start_pos = new_pos
                    
            pos += 1
        if start_pos < len(text):
            ret.append(text[start_pos:])
        return ret

    def find_matching(self, text, start_pos, end_str):
        pos = start_pos
        stack = []
        end_str_len = len(end_str)
        stop_pos = len(text) - end_str_len
        #print('   -> looking for "{}" in "{}"'.format(end_str, text[start_pos:]))
        while True:
            if pos > stop_pos:
                #print('      -> reached end of string :( ({} >= {})'.format(pos, stop_pos))
                return None
            if (len(stack) == 0) and (pos <= stop_pos) and (text[pos:pos+end_str_len] == end_str):
                #print('      -> found it before "{}"!'.format(text[pos+end_str_len:]))
                return pos + end_str_len
            if (len(stack) > 0) and (stack[-1] == text[pos]):
                stack.pop()
            elif text[pos] == '[':
                stack.append(']')
            elif text[pos] == '(':
                stack.append(')')
            elif text[pos] == '\\':
                pos += 1
            pos += 1

    def parse_special(self, text, pos):
        #print('-> parse_special("{}")'.format(text[pos:]))
        
        if (pos == 0) and (text[pos] == '#'):
            return (len(text), HeaderElement(text))

        if (pos == 0) and (text[pos] == '|'):
            return (len(text), TableElement(text, self))

        if (pos == 0) and (text[pos] == '-'):
            items = [ self.parse_text(item.strip()) for item in re.split(r'^-\s*', text, flags=re.MULTILINE) if item.strip() ]
            return (len(text), ListElement(items))

        if text[pos] == '*':
            if (pos+1 < len(text)) and (text[pos:pos+2] == '**'):
                fmt = '**'
            else:
                fmt = '*'
            end_pos = text.find(fmt, pos+len(fmt))
            if end_pos >= 0:
                children = self.parse_text(text[pos+len(fmt):end_pos])
                return (end_pos+len(fmt), TextFormatElement(fmt, children))
                
        if text[pos] == '`':
            close_pos = text.find('`', pos+1)
            if close_pos > pos:
                return (close_pos+1, CodeElement(text[pos+1:close_pos]))

        if (pos+1 < len(text)) and (text[pos:pos+2] == '{%'):
            next_pos = self.find_matching(text, pos+2, '%}')
            if next_pos is not None:
                return (next_pos, CommandElement(text[pos+2:next_pos-2]))

        if (pos+1 < len(text)) and (text[pos:pos+2] == '!['):
            paren_pos = self.find_matching(text, pos+2, ']')
            if (paren_pos is not None) and (paren_pos < len(text)) and (text[paren_pos] == '('):
                next_pos = self.find_matching(text, paren_pos+1, ')')
                if next_pos is not None:
                    alt = text[pos+2:paren_pos-1]
                    url = text[paren_pos+1:next_pos-1]
                    return (next_pos, ImageElement(url, alt))
        
        if text[pos] == '[':
            paren_pos = self.find_matching(text, pos+1, ']')
            if (paren_pos is not None) and (paren_pos < len(text)) and (text[paren_pos] == '('):
                next_pos = self.find_matching(text, paren_pos+1, ')')
                if next_pos is not None:
                    label_els = self.parse_text(text[pos+1:paren_pos-1])
                    link_text = text[paren_pos+1:next_pos-1]
                    return (next_pos, LinkElement(link_text, label_els))
        
        return (0, None)
                
