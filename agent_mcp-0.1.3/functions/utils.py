from typing import Dict, List, Any, Union
import datetime

# Import the specific Firestore timestamp types
try:
    from google.cloud.firestore_v1.base_document import DatetimeWithNanoseconds
except ImportError:
    # Handle cases where the specific type might not be directly importable
    # or if using an older/different version of the library.
    DatetimeWithNanoseconds = None # Rely on datetime.datetime check

try:
    # Also handle the base Timestamp type
    from google.cloud.firestore_v1.types.base import Timestamp
except ImportError:
    Timestamp = None # Rely on datetime.datetime check if this fails

# Define the types to check against - use tuple for isinstance
TIMESTAMP_TYPES = (datetime.datetime,) # datetime.datetime covers DatetimeWithNanoseconds
if Timestamp:
    TIMESTAMP_TYPES += (Timestamp,)


def convert_timestamps_to_isoformat(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """Recursively convert Firestore/datetime timestamp fields to ISO format strings."""
    if isinstance(data, dict):
        # Recursively process dictionary values
        return {k: convert_timestamps_to_isoformat(v) for k, v in data.items()}
    elif isinstance(data, list):
        # Recursively process list items
        return [convert_timestamps_to_isoformat(item) for item in data]
    elif isinstance(data, TIMESTAMP_TYPES):
        # Check if the item is one of the timestamp types we handle
        try:
            # Ensure timezone info is present (assume UTC if naive)
            if data.tzinfo is None:
                 dt_aware = data.replace(tzinfo=datetime.timezone.utc)
            else:
                 dt_aware = data
            return dt_aware.isoformat()
        except Exception as e:
            # Fallback in case isoformat fails for some reason
            print(f"Warning: Could not convert timestamp {data} to ISO format: {e}")
            return str(data) # Convert to basic string as fallback
    else:
        # Return data unchanged if it's not a dict, list, or known timestamp type
        return data