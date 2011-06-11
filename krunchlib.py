# krunchlib.py is part of krunch.
# 
# krunch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# krunch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with krunch.  If not, see <http://www.gnu.org/licenses/>.

from urllib import urlopen

class Krunch():
    """
    The core class of the krunch library. Used to retrieve shortened URLs from
    various services.

    Instance variables:
    service - the URL to which the longer URL is appended. No default, must be set
        when instantiating the Krunch class. ex: 'http://is.gd/api.php?longurl='
    """
    
    service = ""
    
    def __init__(self, service):
        self.service = service
        
    def krunch_url(self, url):
        """
        Accepts a URL to be shortened and returns that shortened URL.
        
        Performs a urllib.urlopen of the service and url, and reads the resulting
        shorter url. Does not process the URL at all, so any desired formatting
        or QA must happen in the client. If the retrieval is unsuccessful, returns
        False.
        """
        
        try:
            response = urlopen(self.service + url)
            return response.read()
        except Exception, e:
            print >> sys.stderr, 'Error: Could not connect to URL shortening \
            service.\nException: %s' % e
            return False