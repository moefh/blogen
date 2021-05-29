
import os
import re
import PIL.Image

import blogenlib

class Renderer:
    """Markdown renderer

    Most of the rendering job is done by the markdown elements.  This
    class just starts the rendering and helps with miscellaneous tasks
    like processing markdown commands and reading information from
    image files.

    """

    def __init__(self, cfg, src, copy_files):
        self.cfg = cfg
        self.src = src
        self.copy_files = copy_files
        self.image_cache = {}

    def _parse_command_args(self, txt):
        ret = []
        pos = 0
        while pos < len(txt):
            while (pos < len(txt)) and (txt[pos] in ' \t\r\n'):
                pos += 1
            if pos >= len(txt):
                break
            if txt[pos] == "'":
                # read up to next "'", processing slashes
                pos += 1
                chars = []
                while pos < len(txt):
                    c = txt[pos]
                    pos += 1
                    if c == "'":
                        break
                    if (c == '\\') and (pos < len(txt)):
                        chars.append(blogenlib.markdown.Element.slashed_char(txt[pos]))
                        pos += 1
                    else:
                        chars.append(c)
                ret.append(''.join(chars))
            else:
                # read up to next space
                start = pos
                while (pos < len(txt)) and (txt[pos] not in ' \t\r\n'):
                    pos += 1
                ret.append(txt[start:pos])
        return ret
    
    def _cmd_error(self, msg):
        return '<span style="background-color: #833; color: #fff;">' + msg + '</span>'
    
    def _cmd_post_link(self, args_text):
        args = self._parse_command_args(args_text)
        if len(args) == 0:
            return self._cmd_error('post_link command must be given a post name')
        post_name = args[0]
        post = self.src.get_post(post_name)
        if post is None:
            return self._cmd_error('post_link: post "{}" not found'.format(post_name))
        link_url = post.get_publish_url()
        link_text = args[1] if (len(args) > 1) else post.get_title()
        return '<a href="{}">{}</a>'.format(link_url, link_text)

    def _cmd_tag_archive_link(self, args_text):
        args = self._parse_command_args(args_text)
        if len(args) == 0:
            return self._cmd_error('_cmd_tag_archive_link command must be given a tag name')
        tag_name = args[0]
        link_url = blogenlib.url_join(self.cfg.v.publish_url, 'tags', tag_name)
        link_text = args[1] if len(args) > 1 else link_url
        return '<a href="{}">{}</a>'.format(link_url, link_text)

    def process_command(self, cmd):
        """Render a markdown {% command %}"""
        
        match = re.fullmatch(r'([^\s]+)\s+(.*)', cmd)
        if match:
            command = match.group(1)
            args = match.group(2)
        else:
            command = cmd
            args = ''
            
        if command == 'post_link':
            return self._cmd_post_link(args)

        if command == 'tag_archive_link':
            return self._cmd_tag_archive_link(args)

        return self._cmd_error('UNKNOWN COMMAND: ' + blogenlib.markdown.Element.quote_html(command))

    def get_image_info(self, url):
        """Get information for an image given its URL.
        
        If the URL is in the form "Page-Name/filename", the URL will be converted
        to an URL pointing to the filename in the post directory, and its width
        and height will be read from the image file (if possible).
        """
        
        if url in self.image_cache:
            return self.image_cache[url]
        ret = { 'url' : url }

        # get the page containing the image for the URL
        (page_name, filename) = url.split('/', maxsplit = 1)
        page = self.src.get_page(page_name)
        if page is None:
            return ret
        ret['url'] = blogenlib.url_join(page.get_publish_url(), filename)

        # read the image dimensions
        src_file = os.path.join(page.get_source_dir(), filename)
        dst_file = os.path.join(page.get_publish_dir(), filename)
        try:
            with PIL.Image.open(src_file) as img:
                width, height = img.size
                ret['width'] = str(width)
                ret['height'] = str(height)
        except:
            # ignore errors reading image (might be an unknown file format)
            pass

        # add file to the list of files to publish
        self.copy_files.add(src_file, dst_file)
        
        self.image_cache[url] = ret
        return ret

    def render(self, markdown):
        """Render the markdown to HTML."""
        return markdown.render(self)
        
