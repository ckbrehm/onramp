"""Encapsulation of functionality provided by various batch schedulers.

Exports:
    SLURMScheduler: Interface to SLURM batch scheduler.
    Scheduler: Generic instantiator for all implemented schedulers.
"""
import logging
import os
from subprocess import CalledProcessError, check_output, STDOUT

class _BatchScheduler(object):
    """Superclass for batch scheduler classes.

    Subclasses must override the non-magic methods defined here.
    """
    @classmethod
    def is_scheduler_for(cls, type):
        """Return boolean indicating whether the class provides an interface to
        the batch scheduler type given.

        Args:
            type (str): Batch scheduler type.
        """
        pass

    def get_batch_script(self, run_name, numtasks=4, email=None):
        """Return the batch script that runs a job as per args formatted for the
        given batch scheduler.

        Args:
            run_name (str): Human-readable label for job run.
            num_tasks (int): Number of tasks to schedule.
            email (str): Email to send results to upon completion. If None, no
                email sent.
        """
        pass

    def schedule(self, proj_loc):
        """Schedule a job using the given batch scheduler.

        Args:
            proj_loc (str): Folder containing the batch script 'script.sh' for
                the job to schedule.
        """
        pass

    def check_status(self, scheduler_job_num):
        """Return job status from scheduler.

        Args:
            scheduler_job_num (int): Job number of the job to check state on as
                given by the scheduler, not as given by OnRamp.
        """
        pass

    def cancel_job(self, scheduler_job_num):
        """Cancel the given job.
    
        Args:
            scheduler_job_num (int): Job number, as given by the scheduler, of the
                job to cancel.
        """
        pass
        
    def __init__(self, type):
        """Set batch scheduler type and return the instance.

        Args:
            type (str): Batch scheduler type.
        """
        pass

class SLURMScheduler(_BatchScheduler):
    @classmethod
    def is_scheduler_for(cls, type):
        """Return boolean indicating whether the class provides an interface to
        the batch scheduler type given.

        Args:
            type (str): Batch scheduler type.
        """
        return type == 'SLURM'

    def get_batch_script(self, run_name, numtasks=4, email=None):
        """Return the batch script that runs a job as per args formatted for the
        SLURM batch scheduler.

        Args:
            run_name (str): Human-readable label for job run.
            num_tasks (int): Number of tasks to schedule.
            email (str): Email to send results to upon completion. If None, no
                email sent.
        """
        contents = '#!/bin/bash\n'
        contents += '\n'
        contents += '###################################\n'
        contents += '# Slurm Submission options\n'
        contents += '#\n'
        contents += '#SBATCH --job-name=' + run_name + '\n'
        contents += '#SBATCH -o output.txt\n'
        contents += '#SBATCH -n ' + str(numtasks) + '\n'
        if email:
            self.logger.debug('%s configured for email reporting to %s'
                              % (run_name, email))
            contents += '#SBATCH --mail-user=' + email + '\n'
        contents += '###################################\n'
        contents += '\n'
        contents += 'python bin/onramp_run.py\n'
        return contents
        
    def schedule(self, proj_loc):
        """Schedule a job using the SLURM batch scheduler.

        Args:
            proj_loc (str): Folder containing the batch script 'script.sh' for
                the job to schedule.
        """
        ret_dir = os.getcwd()
        os.chdir(proj_loc)
        try:
            batch_output = check_output(['sbatch', 'script.sh'], stderr=STDOUT)
        except CalledProcessError as e:
            msg = 'Job scheduling call failed'
            os.chdir(ret_dir)
            return {
                'returncode': e.returncode,
                'msg': '%s: %s' % (msg, e.output)
            }
        os.chdir(ret_dir)
        output_fields = batch_output.strip().split()

        if 'Submitted batch job' != ' '.join(output_fields[:-1]):
            msg = 'Unexpeted output from sbatch'
            self.logger.error(msg)
            return {
                'status_code': -7,
                'status_msg': msg
            }

        try:
            job_num = int(output_fields[3:][0])
        except ValueError, IndexError:
            msg = 'Unexpeted output from sbatch'
            self.logger.error(msg)
            return {
                'status_code': -7,
                'status_msg': msg
            }

        return {
            'status_code': 0,
            'status_msg': 'Job %d scheduled' % job_num,
            'job_num': job_num
        }

    def check_status(self, scheduler_job_num):
        """Return job status from scheduler.

        Args:
            scheduler_job_num (int): Job number of the job to check state on as
                given by the scheduler, not as given by OnRamp.
        """
        try:
            job_info = check_output(['scontrol', 'show', 'job',
                                     str(scheduler_job_num)])
        except CalledProcessError as e:
            msg = 'Job info call failed'
            self.logger.error(msg)
            return (-1, msg)

        job_state = job_info.split('JobState=')[1].split()[0]
        if job_state == 'RUNNING':
            return (0, 'Running')
        elif job_state == 'COMPLETED':
            return (0, 'Done')
        elif job_state == 'PENDING':
            return (0, 'Queued')
        elif job_state == 'FAILED':
            msg = 'Job failed'
            self.logger.error(msg)
            return (-1, msg)
        else:
            msg = 'Unexpected job state from scheduler'
            self.logger.error(msg)
            return (-2, msg)

    def cancel_job(self, scheduler_job_num):
        """Cancel the given job.
    
        Args:
            scheduler_job_num (int): Job number, as given by the scheduler, of the
                job to cancel.
        """
        try:
            result = check_output(['scancel', str(scheduler_job_num)], stderr=STDOUT)
        except CalledProcessError as e:
            msg = 'Job cancel call failed'
            self.logger.error(msg)
            return (-1, msg)
        return (0, result)

def Scheduler(type):
    """Instantiate the appropriate scheduler class for given type.

    Args:
        type (str): Identifier for batch scheduler type.
    """
    for cls in _BatchScheduler.__subclasses__():
        if cls.is_scheduler_for(type):
            return cls(type)
    raise ValueError
