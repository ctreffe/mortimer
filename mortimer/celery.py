# not uesed

from __future__ import absolute_import

from celery import Celery

celery = Celery('mortimer.celery',
                broker='redis://',
                backend='redis://',
                include=['mortimer.tasks'])

# Optional configuration, see the application user guide.
#celery.conf.update(
    #CELERY_TASK_RESULT_EXPIRES=3600,
#)

if __name__ == '__main__':
    celery.start()
