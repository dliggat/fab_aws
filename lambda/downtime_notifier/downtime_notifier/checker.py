import requests


class Checker(object):

    TIMEOUT = 10

    def __init__(self, url=None, name=None, expected_code=200, expected_text=None):
        """
        Args:
            url: (str) the URL to run a GET against
            name: (str) The name of the site to report in the message
            expected_code: (int) The expected return code of the GET
            expected_text: (str) A string to search for in the returned payload
        """
        assert url and name
        self.url = url
        self.name = name
        self.expected_code = expected_code
        self.expected_text = expected_text
        self._exceptional = False
        self._message = ''

    @property
    def message(self):
        """(str) The summary message."""
        return self._message

    @property
    def exceptional(self):
        """(bool) True if the GET behaved as expected/desired, else False."""
        return self._exceptional


    def check(self):
        """Run a GET on the url, and build a message detailing any exceptional circumstances."""
        try:
            req = requests.get(self.url, timeout=self.TIMEOUT, allow_redirects=False)

        except requests.exceptions.ConnectionError as e:
            self._exceptional = True
            self._message = 'Failed to connect to {0} due to a network problem; result: {1}'.format(self.name, e.message)
            return

        except requests.exceptions.Timeout as e:
            self._exceptional = True
            self._message = 'Timed out connecting to {0}; result: {1}'.format(self.name, e.message)
            return

        except requests.exceptions.RequestException as e:
            self._exceptional = True
            self._message = 'Got an unspecified error connecting to {0}; result: {1}'.format(self.name, e.message)
            return

        # Check the status code against what was expected.
        if req.status_code != self.expected_code:
            self._exceptional = True
            self._message = 'Expected HTTP {0} connecting to {1}; got {2} instead.'.format(
                self.expected_code, self.name, req.status_code)
            return

        # Validate the text against the expectation, if one was supplied.
        if self.expected_text and self.expected_text not in req.text:
            self._exceptional = True
            self._message = 'Expected to find "{0}" in request to {1}; was missing'.format(
                self.expected_text, self.name)
            return

        # Looks like everything worked.
        self._message = 'Successfully connected to {0}; got response {1}!'.format(self.name, self.expected_code)
        return

