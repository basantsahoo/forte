import functools


class ProcessLoggerMixin:
    def log(self, *msgs):
        if self.log_enabled:
            p_id = self.display_id if self.display_id else self.id
            print("***", p_id, *msgs)

    def display_process(function):
        @functools.wraps(function)
        def wrapper(self, *args, **kwargs):
            if self.activated:
                func = function(self, *args, **kwargs)
                return func
            else:
                return None
        return wrapper
