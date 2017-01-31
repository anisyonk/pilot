"""
  Rucio SiteMover

  :author: Mario Lassnig <mario.lassnig@cern.ch>, 2015-2017
"""

from .base import BaseSiteMover

from pUtil import tolog
from PilotErrors import PilotException

from commands import getstatusoutput
from os.path import dirname

import os


class rucioSiteMover(BaseSiteMover):
    """ SiteMover that uses rucio CLI for both get and put functionality """

    name = 'rucio'
    schemes = ['srm', 'gsiftp', 'root', 'https', 's3', 's3+rucio']

    def __init__(self, *args, **kwargs):
        super(rucioSiteMover, self).__init__(*args, **kwargs)

    def __which(self, pgm):
        """
        Do not assume existing which command
        """
        path = os.getenv('PATH')
        for p in path.split(os.path.pathsep):
            p = os.path.join(p, pgm)
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p

    def setup(self):
        """
        Basic setup
        """

        # disable rucio-clients ANSI colours - unneeded in logfiles :-)
        os.environ['RUCIO_LOGGING_FORMAT'] = '{0}%(asctime)s %(levelname)s [%(message)s]'

        # be verbose about the execution environment
        s, o = getstatusoutput('python -v -c "import gfal2" 2>&1 | grep dynamically')
        tolog('rucio_environment=%s' % str(os.environ))
        tolog('which rucio: %s' % self.__which('rucio'))
        tolog('which gfal2: %s' % o)
        tolog('which gfal-copy: %s' % self.__which('gfal-copy'))


    def resolve_replica(self, fspec, protocol, ddm=None):
        """
        Overridden method -- unused
        """

        return {'ddmendpoint': fspec.replicas[0][0] if fspec.replicas else None,
                'surl': None,
                'pfn': fspec.lfn}

    def stageIn(self, turl, dst, fspec):
        """
        Use the rucio download command to stage in the file.

        :param turl:  overrides parent signature -- unused
        :param dst:   overrides parent signature -- unused
        :param fspec: dictionary containing destination replicas, scope, lfn
        :return:      destination file details (ddmendpoint, surl, pfn)
        """

        if fspec.replicas:
            cmd = 'rucio download --dir %s --rse %s %s:%s' % (dirname(dst),
                                                              fspec.replicas[0][0],
                                                              fspec.scope,
                                                              fspec.lfn)
        else:
            cmd = 'rucio download --dir %s --rse %s --pfn %s %s:%s' % (dirname(dst),
                                                                       fspec.ddmendpoint,
                                                                       fspec.turl,
                                                                       fspec.scope,
                                                                       fspec.lfn)
        tolog('stageIn: %s' % cmd)
        s, o = getstatusoutput(cmd)
        if s:
            raise PilotException('stageIn failed -- rucio download did not succeed: %s' % o.replace('\n', ''))

        # TODO: fix in rucio download to set specific outputfile
        #       https://its.cern.ch/jira/browse/RUCIO-2063
        cmd = 'mv %s %s' % (dirname(dst) + '/%s/%s' % (fspec.scope,
                                                       fspec.lfn),
                            dst)
        tolog('stageInCmd: %s' % cmd)
        s, o = getstatusoutput(cmd)
        tolog('stageInOutput: %s' % o)

        if s:
            raise PilotException('stageIn failed -- could not move downloaded file to destination: %s' % o.replace('\n', ''))


        return {'ddmendpoint': fspec.replicas[0][0] if fspec.replicas else fspec.ddmendpoint,
                'surl': None,
                'pfn': fspec.lfn}

    def stageOut(self, src, dst, fspec):
        """
        Use the rucio upload command to stage out the file.

        :param src:   overrides parent signature -- unused
        :param dst:   overrides parent signature -- unused
        :param fspec: dictionary containing destination ddmendpoint, scope, lfn
        :return:      destination file details (ddmendpoint, surl, pfn)
        """

        cmd = 'rucio upload --no-register --rse %s --scope %s %s' % (fspec.ddmendpoint,
                                                                     fspec.scope,
                                                                     fspec.pfn if fspec.pfn else fspec.lfn)
        tolog('stageOutCmd: %s' % cmd)
        s, o = getstatusoutput(cmd)
        tolog('stageOutOutput: %s' % o)

        if s:
            raise PilotException('stageOut failed -- rucio upload did not succeed: %s' % o.replace('\n', ''))

        return {'ddmendpoint': fspec.ddmendpoint,
                'surl': fspec.surl,
                'pfn': fspec.lfn}
