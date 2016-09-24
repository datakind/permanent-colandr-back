
def assign_status(screenings, num_screeners):
    """
    Assign a status to a citation or fulltext, depending on the status decisions
    of all existing screenings and the number of required screeners.
    """
    num_screenings = len(screenings)
    if num_screenings == 0:
        return 'not_screened'
    elif num_screenings < num_screeners:
        if num_screenings == 1:
            return 'screened_once'
        else:
            return 'screened_twice'
    else:
        statuses = tuple(screening.status for screening in screenings)
        if all(status == 'excluded' for status in statuses):
            return 'excluded'
        elif all(status == 'included' for status in statuses):
            return 'included'
        else:
            return 'conflict'
