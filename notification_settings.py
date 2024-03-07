from operation_message import OperationMessageOptions


# Moved to separate file to avoid circular imports
NOTIFICATION_OPTIONS = {
    'UPCOMING_OPS': OperationMessageOptions(),
    '30MIN_OPS': OperationMessageOptions(show_game=False, show_date_end=False, include_timestamp=False)
}
