"""Export static learning content while omitting only its local UI controls."""
import copy
from improve_neighborhood_phase9 import body as existing_body, spaced, identity

def body(doc, page):
    clean = copy.deepcopy(doc)
    for form in clean.xpath('//main//form[@data-guide-recorder or @data-guide-filter or @data-teacher-filter or @data-education-filter or @data-education-locator]'):
        form.drop_tree()
    for fallback in clean.xpath('//main//noscript[@data-teacher-fallback or @data-education-fallback]'):
        fallback.drop_tree()
    for element in clean.xpath('//main//time'):
        element.tag = 'span'
    return existing_body(clean, page)
