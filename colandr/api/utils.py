
def assign_status(screening_statuses, num_screeners):
    """
    Assign a status to a citation or fulltext, depending on the status decisions
    of all existing screenings and the number of required screeners.

    Args:
        screening_statuses (List[str] or Tuple[str])
        num_screeners (int)

    Returns:
        str: one of 'not_screened', 'screened_once', 'screened_twice',
            'included', or 'excluded'
    """
    num_screenings = len(screening_statuses)
    if num_screenings == 0:
        return 'not_screened'
    elif num_screenings < num_screeners:
        if num_screenings == 1:
            return 'screened_once'
        else:
            return 'screened_twice'
    else:
        if all(status == 'excluded' for status in screening_statuses):
            return 'excluded'
        elif all(status == 'included' for status in screening_statuses):
            return 'included'
        else:
            return 'conflict'
