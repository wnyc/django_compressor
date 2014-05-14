from compressor.conf import settings
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE


class JsCompressor(Compressor):

    def __init__(self, content=None, output_prefix="js", context=None):
        super(JsCompressor, self).__init__(content, output_prefix, context)
        self.filters = list(settings.COMPRESS_JS_FILTERS)
        self.type = output_prefix

    def split_contents(self):
        if self.split_content:
            return self.split_content
        for elem in self.parser.js_elems():
            attribs = self.parser.elem_attribs(elem)
            if 'src' in attribs:
                basename = self.get_basename(attribs['src'])
                try:
                    filename = self.get_filename(basename)
                except AttributeError:
                    filename = basename
                    
                content = (SOURCE_FILE, filename, basename, elem)
                self.split_content.append(content)
            else:
                content = self.parser.elem_content(elem)
                self.split_content.append((SOURCE_HUNK, content, None, elem))
        return self.split_content

class S3JsCompressor(JsCompressor):
    def get_cached_filenames(self):
        filenames = tuple(filename.get('attrs_dict', {}).get('src','')\
                for filename in self.parser.js_elems())
        return filenames
