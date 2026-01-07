"""Enhanced utilities for exporting travel itineraries to beautiful PDFs."""

import os
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from typing import Optional, List

from django.utils import timezone
import pytz

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Flowable,
)

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from adventures.models import (
    Checklist,
    Collection,
    CollectionItineraryDay,
    CollectionItineraryItem,
    Location,
    Lodging,
    Note,
    Transportation,
    Visit,
)


class Colors:
    """Modern color palette."""
    PRIMARY = colors.HexColor("#2563eb")
    PRIMARY_DARK = colors.HexColor("#1e40af")
    SECONDARY = colors.HexColor("#7c3aed")
    SUCCESS = colors.HexColor("#059669")
    GRAY_50 = colors.HexColor("#f9fafb")
    GRAY_100 = colors.HexColor("#f3f4f6")
    GRAY_200 = colors.HexColor("#e5e7eb")
    GRAY_300 = colors.HexColor("#d1d5db")
    GRAY_600 = colors.HexColor("#4b5563")
    GRAY_700 = colors.HexColor("#374151")
    GRAY_900 = colors.HexColor("#111827")


class DividerLine(Flowable):
    """Horizontal divider line."""
    
    def __init__(self, width, color=None, thickness=1):
        Flowable.__init__(self)
        self.width = width
        self.color = color or Colors.GRAY_200
        self.thickness = thickness
        
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)


def _safe_text(value):
    """Return dash if value is None/empty, otherwise string."""
    if value in (None, ""):
        return "—"
    return str(value).strip()


def _convert_to_timezone(dt, tz_string):
    """Convert UTC datetime to specified timezone."""
    if not dt or not tz_string:
        return dt
    
    try:
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, pytz.UTC)
        target_tz = pytz.timezone(tz_string)
        return dt.astimezone(target_tz)
    except Exception:
        return dt


def _fmt_date(value, include_time=False, tz_string=None):
    """Format date/datetime objects with optional timezone conversion."""
    if not value:
        return "—"
    
    if isinstance(value, datetime):
        if include_time and tz_string:
            value = _convert_to_timezone(value, tz_string)
        else:
            value = timezone.localtime(value)
        
        if include_time:
            tz_abbr = ""
            if hasattr(value, 'tzinfo') and value.tzinfo:
                try:
                    tz_abbr = f" {value.strftime('%Z')}"
                except:
                    pass
            return value.strftime("%b %d, %Y at %I:%M %p") + tz_abbr
        return value.strftime("%b %d, %Y")
    
    return value.strftime("%b %d, %Y")


def _get_image_path(obj) -> Optional[str]:
    """Get image path for any object with images."""
    image = None

    if isinstance(obj, Collection) and obj.primary_image and obj.primary_image.image:
        image = obj.primary_image

    if image is None and hasattr(obj, "images"):
        primary = obj.images.filter(is_primary=True).first()
        image = primary or obj.images.first()

    if image and image.image and hasattr(image.image, "path"):
        if os.path.isfile(image.image.path):
            return image.image.path
    return None


def _create_qr_code(data: str, size=0.8*inch) -> Optional[Image]:
    """Generate QR code for URLs."""
    if not HAS_QRCODE or not data:
        return None
    
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=Colors.GRAY_900, back_color=colors.white)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return Image(buffer, width=size, height=size)
    except Exception:
        return None


def _build_table(data, col_widths=None, style_type="default"):
    """Build styled tables."""
    if style_type == "default":
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), Colors.PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, Colors.GRAY_50]),
            ("LINEBELOW", (0, 0), (-1, 0), 2, Colors.PRIMARY_DARK),
            ("GRID", (0, 1), (-1, -1), 0.5, Colors.GRAY_200),
        ])
    else:
        style = TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, Colors.GRAY_200),
        ])
    
    table = Table(data, colWidths=col_widths or None, repeatRows=1)
    table.setStyle(style)
    return table


def _get_item_icon_and_color(item):
    """Get icon text and color for item type."""
    if isinstance(item, Transportation):
        type_lower = (item.type or "").lower()
        if "flight" in type_lower or "plane" in type_lower:
            return "[FLIGHT]", Colors.PRIMARY
        elif "train" in type_lower:
            return "[TRAIN]", Colors.SECONDARY
        elif "car" in type_lower:
            return "[CAR]", Colors.SUCCESS
        elif "bus" in type_lower:
            return "[BUS]", Colors.GRAY_600
        return "[TRANSPORT]", Colors.PRIMARY
    elif isinstance(item, Lodging):
        return "[HOTEL]", Colors.SECONDARY
    elif isinstance(item, Visit):
        return "[VISIT]", Colors.SUCCESS
    elif isinstance(item, Note):
        return "[NOTE]", Colors.GRAY_600
    elif isinstance(item, Checklist):
        return "[CHECKLIST]", Colors.PRIMARY
    return "", Colors.GRAY_600


def _describe_item(item, styles):
    """Create description of itinerary item with colored icon."""
    icon, color = _get_item_icon_and_color(item)
    icon_html = f'<font color="{color}"><b>{icon}</b></font>'
    
    if isinstance(item, Transportation):
        parts = [item.name or "Transportation"]
        if item.flight_number:
            parts.append(f"Flight {item.flight_number}")
        return icon_html + " " + " • ".join(parts)
    
    elif isinstance(item, Lodging):
        return f"{icon_html} {item.name or 'Lodging'}"
    
    elif isinstance(item, Visit):
        location_name = item.location.name if item.location else "Visit"
        return f"{icon_html} {location_name}"
    
    elif isinstance(item, Note):
        return f"{icon_html} {item.name or 'Note'}"
    
    elif isinstance(item, Checklist):
        total = item.checklistitem_set.count()
        done = item.checklistitem_set.filter(is_checked=True).count()
        return f"{icon_html} {item.name or 'Checklist'} ({done}/{total} complete)"
    
    return str(item)


def _create_item_card(item, styles) -> List:
    """Create visually rich card for itinerary item."""
    elements = []
    
    elements.append(Spacer(1, 4))
    
    # Get image if available
    img_path = _get_image_path(item)
    
    # Build content elements
    content_elements = []
    
    # Title with icon
    title = _describe_item(item, styles)
    content_elements.append(Paragraph(title, styles["ItemTitle"]))
    content_elements.append(Spacer(1, 6))
    
    # Build details
    details = []
    
    if isinstance(item, Transportation):
        start_tz = getattr(item, 'start_timezone', None)
        end_tz = getattr(item, 'end_timezone', None)
        
        if item.from_location or item.to_location:
            route = f"{_safe_text(item.from_location)} → {_safe_text(item.to_location)}"
            if route != "— → —":
                details.append(["Route:", route])
        
        if item.date:
            details.append(["Departure:", _fmt_date(item.date, True, start_tz)])
        if item.end_date:
            details.append(["Arrival:", _fmt_date(item.end_date, True, end_tz)])
        if item.type:
            details.append(["Type:", item.type])
        if item.price:
            details.append(["Cost:", f"{item.price_currency or '$'}{item.price}"])
    
    elif isinstance(item, Lodging):
        lodging_tz = getattr(item, 'timezone', None)
        
        if item.check_in:
            details.append(["Check-in:", _fmt_date(item.check_in, True, lodging_tz)])
        if item.check_out:
            details.append(["Check-out:", _fmt_date(item.check_out, True, lodging_tz)])
        if item.location:
            details.append(["Location:", item.location])
        if item.reservation_number:
            details.append(["Confirmation:", item.reservation_number])
        if item.price:
            details.append(["Cost:", f"{item.price_currency or '$'}{item.price}"])
    
    elif isinstance(item, Visit):
        if item.start_date:
            details.append(["Dates:", f"{_fmt_date(item.start_date)} to {_fmt_date(item.end_date)}"])
        if hasattr(item, 'notes') and item.notes:
            note_text = item.notes[:150] + "..." if len(item.notes) > 150 else item.notes
            details.append(["Notes:", note_text])
    
    elif isinstance(item, Note):
        if item.content:
            content_text = item.content[:150] + "..." if len(item.content) > 150 else item.content
            details.append(["Content:", content_text])
    
    elif isinstance(item, Checklist):
        items_list = item.checklistitem_set.all()
        if items_list:
            checked = [i.name for i in items_list if i.is_checked]
            unchecked = [i.name for i in items_list if not i.is_checked]
            if checked:
                details.append(["Completed:", ", ".join(checked[:5])])
            if unchecked:
                details.append(["Remaining:", ", ".join(unchecked[:5])])
    
    # Add details as paragraphs
    for label, value in details:
        detail_text = f'<font color="{Colors.GRAY_600}"><b>{label}</b></font> {value}'
        content_elements.append(Paragraph(detail_text, styles["Normal"]))
        content_elements.append(Spacer(1, 2))
    
    # Create layout with or without image
    if img_path:
        try:
            thumb = Image(img_path, width=1.4*inch, height=1.05*inch)
            layout_table = Table([[content_elements, thumb]], colWidths=[390, 140])
            layout_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
        except Exception:
            layout_table = Table([[content_elements]], colWidths=[540])
            layout_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
    else:
        layout_table = Table([[content_elements]], colWidths=[540])
        layout_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
    
    # Wrap in styled box
    card_box = Table([[layout_table]], colWidths=[556])
    card_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), Colors.GRAY_50),
        ("BOX", (0, 0), (-1, -1), 1, Colors.GRAY_200),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    
    elements.append(card_box)
    
    # Add link with QR code
    link = getattr(item, 'link', None)
    if link:
        elements.append(Spacer(1, 6))
        link_row = []
        
        if HAS_QRCODE:
            qr = _create_qr_code(link, size=0.6*inch)
            if qr:
                link_row.append(qr)
        
        link_text = Paragraph(
            f'<font color="{Colors.PRIMARY}"><b>Link:</b> {link[:60]}{"..." if len(link) > 60 else ""}</font>',
            styles["Small"]
        )
        link_row.append(link_text)
        
        if link_row:
            link_table = Table([link_row], colWidths=[70, 486] if len(link_row) > 1 else [556])
            link_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(link_table)
    
    elements.append(Spacer(1, 16))
    
    return elements


def _build_image_grid(image_paths: List[str], max_width=6.5*inch, images_per_row=3) -> List:
    """Create a grid layout for multiple images."""
    if not image_paths:
        return []
    
    img_width = (max_width / images_per_row) - 8
    img_height = img_width * 0.7
    
    rows = []
    current_row = []
    
    for img_path in image_paths:
        try:
            img = Image(img_path, width=img_width, height=img_height)
            current_row.append(img)
            
            if len(current_row) == images_per_row:
                rows.append(current_row)
                current_row = []
        except Exception:
            continue
    
    if current_row:
        while len(current_row) < images_per_row:
            current_row.append(Spacer(img_width, img_height))
        rows.append(current_row)
    
    result = []
    for row in rows:
        table = Table([row], colWidths=[img_width]*images_per_row)
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        result.append(table)
        result.append(Spacer(1, 8))
    
    return result


def render_collection_pdf(collection: Collection, current_user) -> bytes:
    """Generate beautifully formatted PDF for travel collection."""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=48,
        rightMargin=48,
        topMargin=60,
        bottomMargin=48,
    )
    
    # Setup styles
    styles = getSampleStyleSheet()
    
    if "TripTitle" not in styles:
        styles.add(ParagraphStyle(
            name="TripTitle",
            parent=styles["Title"],
            fontSize=26,
            leading=32,
            textColor=Colors.PRIMARY,
            spaceAfter=12,
            alignment=TA_CENTER,
        ))
    
    if "TripSubtitle" not in styles:
        styles.add(ParagraphStyle(
            name="TripSubtitle",
            fontSize=13,
            leading=16,
            textColor=Colors.GRAY_600,
            spaceAfter=20,
            alignment=TA_CENTER,
        ))
    
    if "SectionTitle" not in styles:
        styles.add(ParagraphStyle(
            name="SectionTitle",
            fontSize=16,
            leading=20,
            textColor=Colors.PRIMARY_DARK,
            spaceBefore=16,
            spaceAfter=10,
            fontName="Helvetica-Bold",
        ))
    
    if "ItemTitle" not in styles:
        styles.add(ParagraphStyle(
            name="ItemTitle",
            fontSize=11,
            leading=14,
            spaceBefore=4,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        ))
    
    if "Small" not in styles:
        styles.add(ParagraphStyle(
            name="Small",
            fontSize=9,
            leading=11,
            textColor=Colors.GRAY_600,
        ))
    
    story = []
    
    # COVER PAGE
    story.append(Spacer(1, 0.75*inch))
    story.append(Paragraph(collection.name or "Travel Itinerary", styles["TripTitle"]))
    
    if collection.start_date and collection.end_date:
        date_range = f"{_fmt_date(collection.start_date)} — {_fmt_date(collection.end_date)}"
        story.append(Paragraph(date_range, styles["TripSubtitle"]))
    
    story.append(Spacer(1, 12))
    
    # Hero image
    hero_path = _get_image_path(collection)
    if hero_path:
        try:
            img = Image(hero_path, width=6*inch, height=4*inch)
            story.append(img)
            story.append(Spacer(1, 16))
        except Exception:
            story.append(Spacer(1, 8))
    
    # Description
    if collection.description:
        desc_table = Table([[Paragraph(collection.description, styles["BodyText"])]], colWidths=[580])
        desc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), Colors.GRAY_50),
            ("BOX", (0, 0), (-1, -1), 1, Colors.GRAY_200),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(desc_table)
        story.append(Spacer(1, 16))
    
    # Quick stats
    story.append(Paragraph('<font color="{}"><b>Trip Overview</b></font>'.format(Colors.PRIMARY), styles["Heading3"]))
    story.append(Spacer(1, 6))
    
    counts = {
        "Locations": (collection.locations.count(), Colors.SUCCESS),
        "Transportation": (collection.transportation_set.count(), Colors.PRIMARY),
        "Lodging": (collection.lodging_set.count(), Colors.SECONDARY),
        "Notes": (collection.note_set.count(), Colors.GRAY_600),
        "Checklists": (collection.checklist_set.count(), Colors.GRAY_600),
    }
    
    stats_data = []
    for label, (count, color) in counts.items():
        stats_data.append([
            Paragraph(f'<b>{label}</b>', styles["Normal"]),
            Paragraph(f'<para alignment="right"><font color="{color}"><b>{count}</b></font></para>', styles["Normal"]),
        ])
    
    stats_table = Table(stats_data, colWidths=[200, 80])
    stats_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), Colors.GRAY_50),
        ("BOX", (0, 0), (-1, -1), 1, Colors.GRAY_200),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, Colors.GRAY_200),
    ]))
    story.append(stats_table)
    
    story.append(PageBreak())
    
    # ITINERARY
    items = list(
        collection.itinerary_items.select_related("content_type").order_by("is_global", "date", "order")
    )
    days = list(collection.itinerary_days.all().order_by("date"))
    
    if items or days:
        story.append(Paragraph("Itinerary", styles["SectionTitle"]))
        story.append(DividerLine(6.5*inch, Colors.PRIMARY, 2))
        story.append(Spacer(1, 12))
        
        # Trip-wide items
        global_items = [i for i in items if i.is_global]
        if global_items:
            story.append(Paragraph("Trip-Wide Items", styles["Heading3"]))
            story.append(Spacer(1, 8))
            
            for item in global_items:
                obj = getattr(item, "item", None)
                if obj:
                    story.extend(_create_item_card(obj, styles))
        
        # Day-by-day
        day_map = {d.date: d for d in days}
        day_keys = sorted(set(
            [day.date for day in days] +
            [item.date for item in items if not item.is_global and item.date]
        ))
        day_items = defaultdict(list)
        for item in items:
            if not item.is_global and item.date:
                day_items[item.date].append(item)
        
        for idx, day_key in enumerate(day_keys, start=1):
            if idx > 1:
                story.append(PageBreak())
            
            meta = day_map.get(day_key)
            day_title = meta.name if meta and meta.name else _fmt_date(day_key)
            
            story.append(Paragraph(
                f'<font color="{Colors.PRIMARY}"><b>Day {idx}</b></font> — {day_title}',
                styles["SectionTitle"]
            ))
            
            if meta and meta.description:
                story.append(Paragraph(meta.description, styles["Normal"]))
                story.append(Spacer(1, 8))
            
            story.append(DividerLine(6.5*inch, Colors.GRAY_200, 1))
            story.append(Spacer(1, 12))
            
            day_item_list = sorted(day_items.get(day_key, []), key=lambda x: x.order)
            
            if not day_item_list:
                story.append(Paragraph('<i>No items scheduled for this day</i>', styles["Normal"]))
                story.append(Spacer(1, 12))
            else:
                for item in day_item_list:
                    obj = getattr(item, "item", None)
                    if obj:
                        story.extend(_create_item_card(obj, styles))
    
    # LOCATIONS
    locations = list(collection.locations.select_related("city", "region", "country").all())
    if locations:
        story.append(PageBreak())
        story.append(Paragraph("Locations", styles["SectionTitle"]))
        story.append(DividerLine(6.5*inch, Colors.PRIMARY, 2))
        story.append(Spacer(1, 12))
        
        for loc in locations:
            story.append(Paragraph(f'<b>{loc.name}</b>', styles["ItemTitle"]))
            story.append(Spacer(1, 6))
            
            # Featured image
            featured_img = _get_image_path(loc)
            if featured_img:
                try:
                    img = Image(featured_img, width=4*inch, height=3*inch)
                    story.append(img)
                    story.append(Spacer(1, 8))
                except Exception:
                    pass
            
            # Details
            details = []
            if loc.city or loc.region or loc.country:
                place_parts = [
                    str(loc.city) if loc.city else None,
                    str(loc.region) if loc.region else None,
                    str(loc.country) if loc.country else None,
                ]
                place = ", ".join([p for p in place_parts if p])
                details.append(["Location:", place])
            
            if loc.rating:
                details.append(["Rating:", f"{loc.rating}/5 stars"])
            
            if loc.description:
                desc_text = loc.description[:150] + "..." if len(loc.description) > 150 else loc.description
                details.append(["About:", desc_text])
            
            if loc.link:
                details.append(["Link:", loc.link[:60] + "..." if len(loc.link) > 60 else loc.link])
            
            if details:
                table_data = []
                for label, value in details:
                    table_data.append([
                        Paragraph(f'<font color="{Colors.GRAY_600}"><b>{label}</b></font>', styles["Small"]),
                        Paragraph(str(value), styles["Normal"]),
                    ])
                
                table = _build_table(table_data, col_widths=[80, 400], style_type="simple")
                story.append(table)
                story.append(Spacer(1, 8))
            
            # Image gallery
            img_paths = [
                img.image.path for img in loc.images.all()
                if img.image and hasattr(img.image, 'path') and os.path.isfile(img.image.path)
            ]
            other_imgs = [p for p in img_paths if p != featured_img][:6]
            if other_imgs:
                story.append(Paragraph('<font color="{}"><b>Photos</b></font>'.format(Colors.GRAY_600), styles["Small"]))
                story.append(Spacer(1, 4))
                story.extend(_build_image_grid(other_imgs, images_per_row=3))
            
            story.append(Spacer(1, 16))
            story.append(DividerLine(6.5*inch, Colors.GRAY_200, 1))
            story.append(Spacer(1, 16))
    
    # COLLABORATORS
    collaborators = []
    if collection.user:
        collaborators.append(collection.user)
    collaborators.extend(list(collection.shared_with.all()))
    collaborators = list({c.id: c for c in collaborators if c}.values())
    
    if collaborators:
        story.append(PageBreak())
        story.append(Paragraph("Collaborators", styles["SectionTitle"]))
        story.append(DividerLine(6.5*inch, Colors.PRIMARY, 2))
        story.append(Spacer(1, 12))
        
        collab_data = [["Name", "Username", "Role"]]
        for user in collaborators:
            name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "—"
            role = "Owner" if user == collection.user else "Collaborator"
            collab_data.append([
                Paragraph(name, styles["Normal"]),
                Paragraph(user.username, styles["Normal"]),
                Paragraph(role, styles["Small"]),
            ])
        
        table = _build_table(collab_data, col_widths=[180, 150, 120])
        story.append(table)
    
    # BRANDING
    story.append(PageBreak())
    story.append(Spacer(1, 3*inch))
    story.append(DividerLine(6.5*inch, Colors.GRAY_300, 1))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        '<para alignment="center"><font color="{}">Created with <b>AdventureLog</b></font></para>'.format(Colors.GRAY_600),
        styles["Normal"]
    ))
    story.append(Paragraph(
        '<para alignment="center"><font color="{}">adventurelog.app</font></para>'.format(Colors.PRIMARY),
        styles["Small"]
    ))
    
    doc.build(story)
    return buffer.getvalue()