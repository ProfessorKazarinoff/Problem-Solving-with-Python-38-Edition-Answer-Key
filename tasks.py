# tasks.py
"""
run

$ invoke build

to make a pdf of all the notebooks in the build/ directory
"""

from pathlib import Path
from invoke import task
import nbformat
from nbformat import NotebookNode
from nbconvert import LatexExporter
from nbconvert.preprocessors import RegexRemovePreprocessor
from nbconvert.writers import FilesWriter
from pandocfilters import applyJSONFilters, RawInline
import re
import shutil

@task
def build(c):
    nb_path_lst = iter_notebook_paths()
    nb_node = merge_notebooks(nb_path_lst)
    output_file_path = Path(Path.cwd(),'build','out.tex')
    export_tex(nb_node, output_file_path)
    src_images_dir_path = Path(Path.cwd(),'images')
    dst_images_dir_path = Path(Path.cwd(),'build','images')
    copy_images_dir(src_images_dir_path,dst_images_dir_path)


def merge_notebooks(nb_path_lst):
    """
    a function that creates a single notebook node object from a list of notebook file paths
    :param filename_lst: lst, a list of .ipynb file paths
    :return: a single notebookNode object
    """
    merged = None
    for fname in nb_path_lst:
        with open(fname, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
        if merged is None:
            merged = nb
        else:
            merged.cells.extend(nb.cells)
    if not hasattr(merged.metadata, "name"):
        merged.metadata.name = ""
    merged.metadata.name += "_merged"
    return merged

def iter_notebook_paths():
    return [f for f in Path.cwd().glob("*.ipynb")]

def export_tex(
    combined_nb_node: NotebookNode, output_file_path: Path, template_file_path=None
):
    resources = {}
    resources["unique_key"] = "combined"
    resources["output_files_dir"] = "combined_files"
    exporter = MyLatexExporter()
    if template_file_path is not None:
        exporter.template_file = str(template_file_path)
    mypreprocessor = RegexRemovePreprocessor()
    mypreprocessor.patterns = ["\s*\Z"]
    exporter.register_preprocessor(mypreprocessor, enabled=True)
    writer = FilesWriter(build_directory=str(output_file_path.parent))
    output, resources = exporter.from_notebook_node(combined_nb_node, resources)
    writer.write(output, resources, notebook_name=output_file_path.stem)

class MyLatexExporter(LatexExporter):
    def default_filters(self):
        yield from super().default_filters()
        yield ("resolve_references", convert_links)

def convert_link(key, val, fmt, meta):
    if key == "Link":
        target = val[2][0]
        # Links to other notebooks
        m = re.match(r"(\d+\-.+)\.ipynb$", target)
        if m:
            return RawInline("tex", "Chapter \\ref{sec:%s}" % m.group(1))

        # Links to sections of this or other notebooks
        m = re.match(r"(\d+\-.+\.ipynb)?#(.+)$", target)
        if m:
            # pandoc automatically makes labels for headings.
            label = m.group(2).lower()
            label = re.sub(r"[^\w-]+", "", label)  # Strip HTML entities
            return RawInline("tex", "Section \\ref{%s}" % label)

    # Other elements will be returned unchanged.


def convert_links(source):
    return applyJSONFilters([convert_link], source)

def copy_images_dir(src_images_dir_path=None, dst_images_dir_path=None):
    if not src_images_dir_path:
        src_images_dir_path = Path(Path.cwd(),'images')
    if not dst_images_dir_path:
        dst_images_dir_path = Path(Path.cwd(),'build','images')
    if dst_images_dir_path.exists():
        shutil.rmtree(dst_images_dir_path)
    shutil.copytree(src_images_dir_path, dst_images_dir_path)
