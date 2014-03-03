# -*- coding: utf-8 -*-
"""
Webstruct supports WebAnnotator_ and GATE_ annotation formats out of box;
WebAnnotator_ is recommended.

Both GATE and WebAnnotator embed annotations into HTML using special tags:
GATE uses custom tags like ``<ORG>`` while WebAnnotator uses tags like
``<span wa-type="ORG">``.

:mod:`webstruct.loaders` classes convert GATE and WebAnnotator tags into
``__START_TAGNAME__`` and ``__END_TAGNAME__`` tokens, clean the HTML
and return the result as a tree parsed by lxml::

    >>> from webstruct import WebAnnotatorLoader  # doctest: +SKIP
    >>> loader = WebAnnotatorLoader()  # doctest: +SKIP
    >>> loader.load('0.html')  # doctest: +SKIP
    <Element html at ...>

Such trees can be processed with utilities from
:mod:`webstruct.feature_extraction`.

.. _WebAnnotator: https://github.com/xtannier/WebAnnotator
.. _GATE: http://gate.ac.uk/
"""
from __future__ import absolute_import
import re
import glob
from itertools import chain
from collections import defaultdict
import lxml.html
import lxml.html.clean

from webstruct.utils import human_sorted, html_document_fromstring
from webstruct import webannotator


class HtmlLoader(object):
    """
    Class for loading unannotated HTML files.
    """
    def __init__(self, encoding=None, cleaner=None):
        self.encoding = encoding
        self.cleaner = cleaner or _get_default_cleaner()

    def load(self, filename):
        with open(filename, 'rb') as f:
            return self.loadbytes(f.read())

    def loadbytes(self, data):
        tree = html_document_fromstring(data, self.encoding)
        return self.cleaner.clean_html(tree)


class WebAnnotatorLoader(HtmlLoader):
    """
    Class for loading HTML annotated using
    `WebAnnotator <https://github.com/xtannier/WebAnnotator>`_.

    .. note::

        Use WebAnnotator's "save format", not "export format".

    """
    def loadbytes(self, data):
        # defer cleaning the tree to prevent custom cleaners from cleaning
        # WebAnnotator markup
        tree = html_document_fromstring(data, encoding=self.encoding)
        webannotator.apply_wa_title(tree)
        entities = self._get_entities(tree)
        self._process_entities(entities)
        return self._cleanup_tree(tree)

    def _get_entities(self, tree):
        entities = defaultdict(list)
        for el in tree.xpath('//span[@wa-id]'):
            entities[el.attrib['wa-id']].append(el)
        return dict(entities)

    def _process_entities(self, entities):
        for _id, elems in entities.items():
            tp = elems[0].attrib['wa-type']
            elems[0].text = ' __START_%s__ %s' % (tp, elems[0].text)
            elems[-1].text = '%s __END_%s__ ' % (elems[-1].text, tp)
            for el in elems:
                el.drop_tag()

    def _cleanup_tree(self, tree):
        for el in tree.xpath('//wa-color'):
            el.drop_tree()

        return self.cleaner.clean_html(tree)


class GateLoader(HtmlLoader):
    """
    Class for loading HTML annotated using `GATE <http://gate.ac.uk/>`_

    >>> import lxml.html
    >>> from webstruct import GateLoader

    >>> loader = GateLoader(known_tags=['ORG', 'CITY'])
    >>> html = b"<html><body><p><ORG>Scrapinghub</ORG> has an <b>office</b> in <CITY>Montevideo</CITY></p></body></html>"
    >>> tree = loader.loadbytes(html)
    >>> lxml.html.tostring(tree)
    '<html><body><p> __START_ORG__ Scrapinghub __END_ORG__  has an <b>office</b> in  __START_CITY__ Montevideo __END_CITY__ </p></body></html>'

    """

    def __init__(self, encoding=None, cleaner=None, known_tags=None):
        if known_tags is None:
            raise ValueError("Please pass `known_tags` argument with a list of all possible tags")
        self.known_tags_ = known_tags
        super(GateLoader, self).__init__(encoding, cleaner)

    def loadbytes(self, data):
        # tags are replaced before parsing data as HTML because
        # GATE's html is invalid
        data = self._replace_tags(data)
        return super(GateLoader, self).loadbytes(data)

    def _replace_tags(self, html_bytes):
        # replace requested tags with unified tokens
        open_re, close_re = self._tag_patterns(self.known_tags_)
        html_bytes = re.sub(open_re, r' __START_\1__ ', html_bytes)
        html_bytes = re.sub(close_re, r' __END_\1__ ', html_bytes)
        return html_bytes

    def _tag_patterns(self, tags):
        tags_pattern = '|'.join(list(tags))
        open_re = re.compile('<(%s)>' % tags_pattern, re.I)
        close_re = re.compile('</(%s)>' % tags_pattern, re.I)
        return open_re, close_re


def load_trees(patterns, verbose=False):
    """
    Load HTML data from several paths/glob patterns,
    maybe using different loaders. Return a list of lxml trees.

    ``patterns`` should be a list of tuples ``(glob_pattern, loader)``.

    Example::

        >>> loader = HtmlLoader()
        >>> patterns = [('path1/*.html', loader), ('path2/*.html', loader)]
        >>> trees = load_trees(patterns)  # doctest: +SKIP

    """
    return chain.from_iterable(
        load_trees_from_files(pat, loader, verbose) for pat, loader in patterns
    )


def load_trees_from_files(pattern, loader, verbose=False):
    """
    Load HTML data using loader ``loader`` from all files matched by
    ``pattern`` glob pattern.
    """
    for path in human_sorted(glob.glob(pattern)):
        if verbose:
            print(path)
        yield loader.load(path)


def _get_default_cleaner():
    return lxml.html.clean.Cleaner(
        style=True,
        scripts=True,
        embedded=True,
        links=True,
        page_structure=False,
        annoying_tags=False,
        meta=False,
        forms=False,
        remove_unknown_tags=False,
        safe_attrs_only=False
    )

