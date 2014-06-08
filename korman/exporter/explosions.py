#    This file is part of Korman.
#
#    Korman is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Korman is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Korman.  If not, see <http://www.gnu.org/licenses/>.

class ExportError(Exception):
    def __init__(self, value="Undefined Export Error"):
        super(Exception, self).__init__(value)


class UndefinedPageError(ExportError):
    mistakes = {}

    def __init__(self):
        super(ExportError, self).__init__("You have objects in pages that do not exist!")

    def add(self, page, obj):
        if page not in self.mistakes:
            self.mistakes[page] = [obj,]
        else:
            self.mistakes[page].append(obj)

    def raise_if_error(self):
        if self.mistakes:
            raise self
