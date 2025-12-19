from typing import List
from datetime import date, timedelta
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from adventures.models import Collection, CollectionItineraryItem, Visit, Lodging, Transportation, Note, Checklist
from rest_framework.exceptions import ValidationError


@transaction.atomic
def auto_generate_itinerary(collection: Collection) -> List[CollectionItineraryItem]:
    """
    Auto-generate itinerary items for a collection based on dated records.
    
    Rules:
    - Visits: Create one item per day of the visit (spanning multiple days)
    - Lodging: Create one item on check_in date only
    - Transportation: Create one item on start date
    - Notes: Create one item on their date if present
    - Checklists: Create one item on their date if present
    
    Order within a day (incremental):
    1. Lodging (check-ins)
    2. Visits
    3. Transportation
    4. Notes
    5. Checklists
    
    Args:
        collection: Collection to generate itinerary for
        
    Returns:
        List[CollectionItineraryItem]: Created itinerary items
        
    Raises:
        ValidationError: If collection already has itinerary items or has no dated records
    """
    
    # Validation: collection must have zero itinerary items
    if collection.itinerary_items.exists():
        raise ValidationError({
            "detail": "Collection already has itinerary items. Cannot auto-generate."
        })
    
    # Get collection date range
    if not collection.start_date or not collection.end_date:
        raise ValidationError({
            "detail": "Collection must have start_date and end_date set."
        })
    
    start_date = collection.start_date
    end_date = collection.end_date
    
    # Collect all items to be added, grouped by date
    items_by_date = {}  # date -> [(content_type, object_id, priority)]
    
    # Priority order for sorting within a day
    PRIORITY_LODGING = 1
    PRIORITY_VISIT = 2
    PRIORITY_TRANSPORTATION = 3
    PRIORITY_NOTE = 4
    PRIORITY_CHECKLIST = 5
    
    # Process Visits: one location item per day of the visit
    # Note: We reference the Location, not the Visit itself
    from adventures.models import Location
    
    visits = Visit.objects.filter(location__collections=collection).select_related('location').distinct()
    for visit in visits:
        if visit.start_date and visit.location:
            visit_start = visit.start_date.date() if hasattr(visit.start_date, 'date') else visit.start_date
            visit_end = visit.end_date.date() if visit.end_date and hasattr(visit.end_date, 'date') else visit_start
            
            # Only include dates within collection range
            visit_start = max(visit_start, start_date)
            visit_end = min(visit_end or visit_start, end_date)
            
            current_date = visit_start
            while current_date <= visit_end:
                if current_date not in items_by_date:
                    items_by_date[current_date] = []
                items_by_date[current_date].append((
                    ContentType.objects.get_for_model(Location),
                    visit.location.id,  # Use Location ID, not Visit ID
                    PRIORITY_VISIT
                ))
                current_date += timedelta(days=1)
    
    # Process Lodging: one item on check_in date only
    lodgings = Lodging.objects.filter(collection=collection)
    for lodging in lodgings:
        if lodging.check_in:
            checkin_date = lodging.check_in.date() if hasattr(lodging.check_in, 'date') else lodging.check_in
            
            # Only include if within collection range
            if start_date <= checkin_date <= end_date:
                if checkin_date not in items_by_date:
                    items_by_date[checkin_date] = []
                items_by_date[checkin_date].append((
                    ContentType.objects.get_for_model(Lodging),
                    lodging.id,
                    PRIORITY_LODGING
                ))
    
    # Process Transportation: one item on start date
    transportations = Transportation.objects.filter(collection=collection)
    for transportation in transportations:
        if transportation.date:
            trans_date = transportation.date.date() if hasattr(transportation.date, 'date') else transportation.date
            
            # Only include if within collection range
            if start_date <= trans_date <= end_date:
                if trans_date not in items_by_date:
                    items_by_date[trans_date] = []
                items_by_date[trans_date].append((
                    ContentType.objects.get_for_model(Transportation),
                    transportation.id,
                    PRIORITY_TRANSPORTATION
                ))
    
    # Process Notes: one item on their date
    notes = Note.objects.filter(collection=collection)
    for note in notes:
        if note.date:
            note_date = note.date.date() if hasattr(note.date, 'date') else note.date
            
            # Only include if within collection range
            if start_date <= note_date <= end_date:
                if note_date not in items_by_date:
                    items_by_date[note_date] = []
                items_by_date[note_date].append((
                    ContentType.objects.get_for_model(Note),
                    note.id,
                    PRIORITY_NOTE
                ))
    
    # Process Checklists: one item on their date
    checklists = Checklist.objects.filter(collection=collection)
    for checklist in checklists:
        if checklist.date:
            checklist_date = checklist.date.date() if hasattr(checklist.date, 'date') else checklist.date
            
            # Only include if within collection range
            if start_date <= checklist_date <= end_date:
                if checklist_date not in items_by_date:
                    items_by_date[checklist_date] = []
                items_by_date[checklist_date].append((
                    ContentType.objects.get_for_model(Checklist),
                    checklist.id,
                    PRIORITY_CHECKLIST
                ))
    
    # Validation: must have at least one dated record
    if not items_by_date:
        raise ValidationError({
            "detail": "No dated records found within collection date range."
        })
    
    # Create itinerary items
    created_items = []
    
    for day_date in sorted(items_by_date.keys()):
        # Sort items by priority within the day
        items = sorted(items_by_date[day_date], key=lambda x: x[2])
        
        for order, (content_type, object_id, priority) in enumerate(items):
            itinerary_item = CollectionItineraryItem.objects.create(
                collection=collection,
                content_type=content_type,
                object_id=object_id,
                date=day_date,
                order=order
            )
            created_items.append(itinerary_item)
    
    return created_items
