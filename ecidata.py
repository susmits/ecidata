#!/usr/bin/env python3

"""
ecidata.py -- Scrape ECI data.

"""

import urllib.request
import xml.etree.ElementTree as ET
import json


#####################################################################
## Data classes.

class candidate_votes(object):
    """
    Votes received by one candidate.

    """
    def __init__(self, candidate, party, votes):
        """
        Instantiate the class with pre-filled values.

        """
        self._candidate = candidate
        self._party = party
        self._votes = votes

    @property
    def candidate(self):
        return self._candidate

    @property
    def party(self):
        return self._party

    @property
    def votes(self):
        return self._votes

    def __repr__(self):
        return "<candidate_votes for %s from %s, %d votes>" % \
            (self.candidate, self.party, self.votes)


class constituency_results(object):
    """
    Results for a constituency.

    """
    def __init__(self, state, constituency, all_votes, declared):
        """
        Instantiate with pre-filled values supplied by the parser.
        `state` is the name of the state.
        `constituency` is the name of the constituency.
        `all_votes` is a list containing `candidate_votes` instances.
        `declared` is True if the results have been declared.

        """
        self._state = state
        self._constituency = constituency
        self._all_candidate_votes = all_votes
        self._declared = declared

    @property
    def state(self):
        return self._state

    @property
    def constituency(self):
        return self._constituency

    @property
    def all_candidate_votes(self):
        return self._all_candidate_votes

    @property
    def declared(self):
        return self._declared

    @property
    def vote_count(self):
        return sum([cv.votes for cv in self.all_candidate_votes])

    def get_votes_for_party(self):
        """
        Returns the votes for one party.

        """

    def __repr__(self):
        return "<constituency_results (%s, %s), %d total votes, " \
            "declared=%s>" % (self.state, self.constituency,
                              self.vote_count, self.declared)


#####################################################################
## Constituency-wise data parser.
##

def _make_constituency_url(state, constituency):
    """
    Generates a URL for a constituency.

    """
    return r"http://eciresults.nic.in/Constituencywise" \
        r"S%d%d.htm?ac=%d" % (state, constituency, constituency)


def _open_constituency(state, constituency):
    """
    Fetches a page for a given constituency.

    """
    url = _make_constituency_url(state, constituency)
    return urllib.request.urlopen(url)


def get_constituency_results(state, constituency):
    """
    Returns a 2-tuple containing a bool which is True if results have
    been declared and a list containing votes received by each
    candidate. Each entry in the list is a dict keyed by three
    strings: 'candidate', 'party', and 'votes'.

    """
    state_name = ""
    constituency_name = ""
    all_votes = []
    declared = False

    next_line_has_results = False
    results_line = ""
    for line in _open_constituency(state, constituency):
        line = line.strip()

        # Cutely, they dump all the data (presumably fetched from
        # some kind of a database and stitched together using some
        # server-side logic?) into one line. So we just trawl through
        # the data till we find that line.
        if line.startswith(b'<div id="div1"'):
            next_line_has_results = True
        elif next_line_has_results:
            results_line = line
            break

    # Now we have some sort of a results line. Let's parse it.
    # First, a few rounds of sanitization.
    results_line = results_line.replace(b'align=left',
                                        b'align="left"')
    results_line = results_line.replace(b'align=right',
                                        b'align="right"')
    results_line = results_line.replace(b'<td></tr>',
                                        b'</td></tr>')

    # Also, we need this encapsulated within some top-level
    # element (rememeber, ET parses XML), so:
    results_line = b'<div>' + results_line + b'</div>'
    parsed = ET.fromstring(results_line)

    # Parsed should have three kids.
    kids = parsed.getchildren()
    assert(len(kids) == 3)
    assert(kids[0].tag == "table")
    result_rows = kids[0].getchildren()

    combined_names = result_rows[0].getchildren()[0].text
    state_name, *constituency_name = combined_names.split(' - ')
    state_name = state_name.strip()
    constituency_name = " - ".join(constituency_name).strip()

    if 'Result Declared' in result_rows[1].getchildren()[0].text:
        declared = True

    # The above two, plus the table header.
    result_rows = result_rows[3:]
    for row in result_rows:
        data = [c.text.strip() for c in row.getchildren()]
        all_votes.append(candidate_votes(data[0], data[1], 
                                         int(data[2])))

    return constituency_results(state_name, constituency_name,
                                all_votes, declared)


#####################################################################
