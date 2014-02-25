# -*- coding: utf-8 -*-
"""
:mod:`webstruct.model` contains convetional wrappers for creating NER models.
"""

from __future__ import absolute_import
import urllib2
from sklearn.pipeline import Pipeline
from webstruct.loaders import HtmlLoader
from webstruct.feature_extraction import HtmlFeatureExtractor, HtmlTokenizer
from webstruct.wapiti import WapitiCRF
from webstruct.sequence_encoding import IobEncoder
from webstruct.features import DEFAULT_FEATURES
from webstruct.utils import smart_join


class NER(object):
    """
    Class for extracting named entities from HTML.

    Initialize it with a trained ``model``. ``model`` must have
    ``transform`` method that accepts lists of
    :class:`webstruct.feature_extraction.HtmlToken` sequences and returns
    lists of predicted IOB2 tags. :func:`create_wapiti_pipeline` function
    returns such model.
    """
    def __init__(self, model, loader=None, html_tokenizer=None):
        self.model = model
        self.loader = loader or HtmlLoader()
        self.html_tokenizer = html_tokenizer or HtmlTokenizer()

    def extract(self, bytes_data):
        """
        Extract named entities from binary HTML data ``bytes_data``.
        Return a list of ``(entity_text, entity_type)`` tuples.
        """
        html_tokens, tags = self.extract_raw(bytes_data)
        groups = IobEncoder.group(zip([tok.token for tok in html_tokens], tags))
        return [
            (smart_join(tokens), tag)
            for (tokens, tag) in groups if tag != 'O'
        ]

    def extract_from_url(self, url):
        """
        A convenience wrapper for :meth:`extract` method that downloads
        input data from a remote URL.
        """
        data = urllib2.urlopen(url).read()
        return self.extract(data)

    def extract_raw(self, bytes_data):
        """
        Extract named entities from binary HTML data ``bytes_data``.
        Return a list of ``(html_token, iob2_tag)`` tuples.
        """
        tree = self.loader.loadbytes(bytes_data)
        html_tokens, _ = self.html_tokenizer.tokenize_single(tree)
        tags = self.model.transform([html_tokens])[0]
        return html_tokens, tags


def create_wapiti_pipeline(model_filename,
                           token_features=None,
                           global_features=None,
                           train_args=None,
                           feature_template=None,
                           min_df=1,
                           **wapiti_kwargs):
    """
    Create a scikit-learn Pipeline for HTML tagging using Wapiti.
    This pipeline expects data produced by
    :class:`webstruct.feature_extraction.HtmlTokenizer`
    as an input and produces sequences of IOB2 tags as output.

    Example of training, with all parameters default::

        >>> import webstruct
        >>> trees = webstruct.load_trees([
        ...    ("train/*.html", webstruct.WebAnnotatorLoader())
        ... ])  # doctest: +SKIP
        >>> X, y = webstruct.HtmlTokenizer().tokenize(trees)  # doctest: +SKIP
        >>> model = webstruct.create_wapiti_pipeline('model.wapiti')  # doctest: +SKIP
        >>> model.fit(X, y)  # doctest: +SKIP

    """

    if token_features is None:
        token_features = DEFAULT_FEATURES

    if train_args is None:
        train_args = '--algo l-bfgs --maxiter 100 --compact --nthread 8 --jobsize 1 --stopwin 15'

    return Pipeline([
        ('fe', HtmlFeatureExtractor(token_features, global_features, min_df=min_df)),
        ('crf', WapitiCRF(model_filename, train_args, feature_template, **wapiti_kwargs)),
    ])

