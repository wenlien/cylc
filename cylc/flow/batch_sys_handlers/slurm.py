# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) NIWA & British Crown (Met Office) & Contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Submits task job scripts to Simple Linux Utility for Resource Management.

.. cylc-scope:: flow.cylc[runtime][<namespace>][job]

Uses the ``sbatch`` command. SLURM directives can be provided in the flow.cylc
file:

.. code-block:: cylc

   [runtime]
       [[my_task]]
           [[[job]]]
               batch system = slurm
               execution time limit = PT1H
           [[[directives]]]
               --nodes = 5
               --account = QXZ5W2

.. note::

   Since not all SLURM commands have a short form, cylc requires
   the long form directives.

These are written to the top of the task job script like this:

.. code-block:: bash

   #!/bin/bash
   #SBATCH --nodes=5
   #SBATCH --time=60:00
   #SBATCH --account=QXZ5W2

If :cylc:conf:`execution time limit` is specified, it is used to generate the
``--time`` directive. Do not specify the ``--time`` directive explicitly if
:cylc:conf:`execution time limit` is specified.  Otherwise, the execution time
limit known by the suite may be out of sync with what is submitted to the batch
system.

Cylc supports heterogeneous Slurm jobs via special numbered directive prefixes
that distinguish repeated directives from one another:

.. code-block:: cylc

   [runtime]
       # run two heterogenous job components:
       script = srun sleep 10 : sleep 30
       [[my_task]]
           [[[job]]]
               batch system = slurm
               execution time limit = PT1H
           [[[directives]]]
               --account = QXZ5W2
               hetjob_0_--mem = 1G  # first prefix must be "0"
               hetjob_0_--nodes = 3
               hetjob_1_--mem = 2G
               hetjob_0_--nodes = 6

The resulting formatted directives are:

.. code-block:: bash

   #!/bin/bash
   #SBATCH --time=60:00
   #SBATCH --account=QXZ5W2
   #SBATCH --mem=1G
   #SBATCH --nodes=3
   #SBATCH hetjob
   #SBATCH --mem=2G
   #SBATCH --nodes=6

.. note::

   For older Slurm versions with *packjob* instead of *hetjob*, use
   ``batch system = slurm_packjob`` and directive prefixes ``packjob_0_`` etc.

.. cylc-scope::

"""

import re
import shlex
import os


class SLURMHandler():
    """SLURM job submission and manipulation."""

    DIRECTIVE_PREFIX = "#SBATCH "
    # Do not include SIGTERM trapping, as SLURM tries to kill the
    # parent script directly with SIGTERM rather than the process
    # group as a whole. In these circumstances, this signal does
    # not get handled. Bash waits for the (unsignalled) child to
    # complete. This does not apply to jobs with proper 'steps'
    # (e.g. using srun within an sbatch script), which are properly
    # signalled.
    # XCPU isn't used by SLURM at the moment, but it's a valid way
    # to manually signal jobs using scancel or sbatch --signal.
    FAIL_SIGNALS = ("EXIT", "ERR", "XCPU")
    KILL_CMD_TMPL = "scancel '%(job_id)s'"
    # N.B. The "squeue -j JOB_ID" command returns 1 if JOB_ID is no longer in
    # the system, so there is no need to filter its output.
    POLL_CMD = "squeue -h"
    REC_ID_FROM_SUBMIT_OUT = re.compile(
        r"\ASubmitted\sbatch\sjob\s(?P<id>\d+)")
    REC_ID_FROM_POLL_OUT = re.compile(r"^ *(?P<id>\d+)")
    SUBMIT_CMD_TMPL = "sbatch '%(job)s'"

    # Heterogeneous job support
    #  Match artificial directive prefix
    REC_HETJOB = re.compile(r"^hetjob_(\d+)_")
    #  Separator between het job directive sections
    SEP_HETJOB = "#SBATCH hetjob"

    @classmethod
    def filter_poll_many_output(cls, out):
        """Return list of job IDs extracted from job poll stdout.

        Needed to avoid the extension for heterogenous jobs ("+0", "+1" etc.)

        """
        job_ids = set()
        for line in out.splitlines():
            m = cls.REC_ID_FROM_POLL_OUT.match(line)
            if m:
                job_ids.add(m.group("id"))
        return list(job_ids)

    @classmethod
    def format_directives(cls, job_conf):
        """Format the job directives for a job file."""
        job_file_path = os.path.expandvars(job_conf['job_file_path'])
        directives = job_conf['directives'].__class__()
        directives['--job-name'] = (
            job_conf['task_id'] + '.' + job_conf['suite_name'])
        directives['--output'] = job_file_path.replace('%', '%%') + ".out"
        directives['--error'] = job_file_path.replace('%', '%%') + ".err"
        if (job_conf["execution_time_limit"] and
                directives.get("--time") is None):
            directives["--time"] = "%d:%02d" % (
                job_conf["execution_time_limit"] / 60,
                job_conf["execution_time_limit"] % 60)
        for key, value in list(job_conf['directives'].items()):
            directives[key] = value
        lines = []
        seen = set()
        for key, value in directives.items():
            m = cls.REC_HETJOB.match(key)
            if m:
                n = m.groups()[0]
                if n != "0" and n not in seen:
                    lines.append(cls.SEP_HETJOB)
                seen.add(n)
                newkey = cls.REC_HETJOB.sub('', key)
            else:
                newkey = key
            if value:
                lines.append("%s%s=%s" % (cls.DIRECTIVE_PREFIX, newkey, value))
            else:
                lines.append("%s%s" % (cls.DIRECTIVE_PREFIX, newkey))
        return lines

    @classmethod
    def get_poll_many_cmd(cls, job_ids):
        """Return the poll command for a list of job IDs."""
        return shlex.split(cls.POLL_CMD) + ["-j", ",".join(job_ids)]


BATCH_SYS_HANDLER = SLURMHandler()
