import os
import sys
import optparse
from collections import namedtuple
from itertools import groupby
from datetime import datetime
from decimal import Decimal


class subtitles(object):

    def __init__(self, file_path, shift_amount, fix_indices):

        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.fix_indices = fix_indices

        if (shift_amount is None):
            self.shift_amount = 0
        else:
            self.shift_amount = shift_amount

        self.chunked_subtitles = []
        # an empty subtitles array to hold 'Subtitle' tuple in future
        self.parsed_subs = []

    def chunk_subs(self):
        '''
        Split "chunks" of our str file, delimited by blank lines.
        Returns a list that contains the content of the file
        '''

        with open(self.file_path) as file:
            self.chunked_subtitles = [
                list(g) for b, g in groupby
                (file, lambda x: bool(x.strip())) if b]

    def parse_file(self):
        '''
        Parsing the chunked file into a list of named tuples.
        This function transforms the time code that is in the file into a
        representation in seconds:
        hh:mm:ss,ms -> ss.ms

        This functions returns a list of named tuples that is built in the
        following order:
        (integer) index   - the index of the chunk
        (decimal) start   - the start time of the subtitles
        (decimal) end     - the end time of the subtitles
        (string[]) content- a list of the content of the subtitles file
        '''

        if self.chunked_subtitles:

            # A representative namedtuples object
            Subtitle = namedtuple('Subtitle', 'index start end content')

            for sub in self.chunked_subtitles:

                # Not strictly necessary, but better safe than sorry
                if len(sub) >= 3:
                    sub = [x.strip() for x in sub]

                    # py3 syntax
                    index, start_end, *content = sub

                    # Split the time code
                    start, end = start_end.split(' --> ')

                    # Transform time code to seconds
                    start_time = self.timecode_to_sec(start)
                    end_time = self.timecode_to_sec(end)

                    # Casting a float value to decimal value to preserve value
                    # after decimal point
                    start_time = Decimal(start_time)
                    end_time = Decimal(end_time)

                    self.parsed_subs.append(Subtitle(index, start_time,
                                                     end_time, content))

        else:
            sys.exit('failed first stage parsing, aborting second stage')

    @staticmethod
    def timecode_to_sec(timecode):
        '''
        Read the time code and represent it using seconds and microseconds.
        Returns a float value of the time code.
        '''
        # Read time code in known format
        time = datetime.strptime(timecode, '%H:%M:%S,%f')

        sec_time = (time.hour * 60 * 60 + time.minute * 60 + time.second +
                    time.microsecond / 1000000)

        return sec_time

    @staticmethod
    def sec_to_timecode(sec):
        '''
        Read the second time representation and turn to time code.
        Returns a string time code representation of a given amount of seconds.
        '''

        # using only the value that is after the decimal point
        ms = str(sec - int(sec))[2:5]

        # divide and module the time into minutes and then into hours
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)

        return ('%(hours)02d:%(minutes)02d:%(seconds)02d,%(microseconds)s' %
                {"hours": h, "minutes": m, "seconds": s, "microseconds": ms})

    def rename_old_file(self):
        '''
        Renames the old file
        '''
        os.rename(self.file_path, self.file_path[
                  :self.file_path.__len__() - 4] + '_old.srt')

    def write_new_file(self):
        '''
        Writes new file with the shifted times, also fixes indices if requested
        '''

        if self.parsed_subs:

            i = 1

            # Open file or create it if it doesn't exist
            with open(self.file_path, 'a') as out:

                for sub in self.parsed_subs:

                    if self.fix_indices is True:
                        sub = sub._replace(index=i)
                        i += 1

                    # Write new time values using the given shift
                    sub = sub._replace(start=sub.start + self.shift_amount)
                    sub = sub._replace(end=sub.end + self.shift_amount)

                    out.write(sub.index + '\n')
                    out.write(self.sec_to_timecode(sub.start) + ' --> ' +
                              self.sec_to_timecode(sub.end) + '\n')

                    # Write the content of the file
                    for con in sub.content:
                        out.write(con + '\n')

                    # Finish each chunk with a new line separator
                    out.write('\n')

        else:
            sys.exit('second stage parsing failed, writing new file aborted')


def main():
    '''
    Should be called on entry point to the module. the main functions parses
    option tags.
    Returns initialization variables.
    '''
    parser = optparse.OptionParser()
    parser.add_option('-p', '--path', dest='path', default=None,
                      help='Path to srt file', type='string')
    parser.add_option('-s', '--shift', dest='shift', default=None,
                      help='Shift in seconds', type='float')
    parser.add_option('-i', '--index', dest='index', action="store_true",
                      help='Run fix indices option')

    (options, _) = parser.parse_args()

    # Keeps looping while the path variable is not a valid path to an srt file
    while options.path is None:
        options.path = input('Enter file path: ')
        if os.path.isfile(options.path) and os.path.exists(options.path):

            _, file_extension = os.path.splitext(options.path)

            if file_extension != '.srt':
                print('Unsupported format: ' + file_extension[1:] + '\n')
                options.path = None
        else:
            print('File not found.\n')
            options.path = None

    # Keeps looping while the shift variable is not a valid value
    while options.shift is None:
        try:
            options.shift = float(input('Enter shift value:'))
        except ValueError:
            print('Value should be a number.\n')
            options.shift = None

    path, shift, fix_indices = options.path, Decimal(
        options.shift), options.index
    subs = subtitles(path, shift, fix_indices)
    subs.chunk_subs()
    subs.parse_file()
    subs.rename_old_file()
    subs.write_new_file()

    if __name__ == "__main__":
        main()