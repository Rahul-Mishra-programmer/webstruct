# -*- coding: utf-8 -*-
from __future__ import absolute_import
import lxml.html
from sklearn.base import BaseEstimator
from .preprocess import IobSequence, Tagset, to_features_and_labels, DEFAULT_TAGSET
from . import features
from .tokenize import default_tokenizer


class HtmlFeaturesExtractor(BaseEstimator):
    """
    Extracts features and labels from html.

    First, we need some features. Feature can depend on current
    token, all other tokens in the same HTML block, all other data in
    document (accessible via 'elem') and on whenever text is from tail
    of element.

        >>> def current_token(index, tokens, elem, is_tail):
        ...     return {'tok': tokens[index]}

    features.CombinedFeatures provides an easy way to combine features::

        >>> from webstruct_token.features import CombinedFeatures, parent_tag
        >>> feature_func = CombinedFeatures(current_token, parent_tag)

    Use HtmlFeaturesExtractor.fit_transform to extract features and labels
    from html data::

        >>> html = "<p>hello <PER>John <b>Doe</b></PER> <br> <PER>Mary</PER> said</p>"
        >>> fe = HtmlFeaturesExtractor(feature_func=feature_func)
        >>> features, labels = fe.fit_transform(html)
        >>> for feat, label in zip(features, labels):
        ...     print("%s %s" % (label, sorted(feat.items())))
        O [('parent_tag', 'p'), ('tok', 'hello')]
        B-PER [('parent_tag', 'p'), ('tok', 'John')]
        I-PER [('parent_tag', 'b'), ('tok', 'Doe')]
        B-PER [('parent_tag', 'p'), ('tok', 'Mary')]
        O [('parent_tag', 'p'), ('tok', 'said')]

    """

    def __init__(self, tokenizer=default_tokenizer, tags=DEFAULT_TAGSET,
                 feature_func=features.DEFAULT, tagset=None, label_encoder=None):
        self.tokenizer = tokenizer
        self.feature_func = feature_func
        if tagset is None:
            self.tagset = Tagset(tags)
        else:
            self.tagset = tagset

        if label_encoder is None:
            self.label_encoder = IobSequence(self.tagset)
        else:
            self.label_encoder = label_encoder

    def _parse_html(self, html):
        return lxml.html.fromstring(html)

    def fit_transform(self, X, y=None):
        """
        Convert HTML data :param:X to lists of feature dicts and labels.
        :param:y is ignored.

        Return (features, labels) tuple.
        """
        html = self.tagset.encode_tags(X)
        doc = self._parse_html(html)
        res = to_features_and_labels(doc, self.tokenizer, self.label_encoder, self.feature_func)
        self.label_encoder.reset()
        if not res:
            return (), ()
        return zip(*res)
