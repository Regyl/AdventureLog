<script lang="ts">
	// @ts-nocheck
	import type {
		Collection,
		CollectionItineraryItem,
		Location,
		Transportation,
		Lodging,
		Note,
		Checklist
	} from '$lib/types';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import { dndzone, TRIGGERS, SHADOW_ITEM_MARKER_PROPERTY_NAME } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';
	import CalendarBlank from '~icons/mdi/calendar-blank';
	import Bed from '~icons/mdi/bed';
	import LocationCard from '$lib/components/LocationCard.svelte';
	import TransportationCard from '$lib/components/TransportationCard.svelte';
	import LodgingCard from '$lib/components/LodgingCard.svelte';
	import NoteCard from '$lib/components/NoteCard.svelte';
	import ChecklistCard from '$lib/components/ChecklistCard.svelte';
	import NewLocationModal from '$lib/components/NewLocationModal.svelte';
	import LodgingModal from '$lib/components/LodgingModal.svelte';
	import TransportationModal from '$lib/components/TransportationModal.svelte';
	import NoteModal from '$lib/components/NoteModal.svelte';
	import ChecklistModal from '$lib/components/ChecklistModal.svelte';
	import ItineraryLinkModal from '$lib/components/ItineraryLinkModal.svelte';

	export let collection: Collection;
	export let user: any;
	// Whether the current user can modify this collection (owner or shared user)
	export let canModify: boolean = false;

	const flipDurationMs = 200;

	// Extended itinerary item with resolved object
	type ResolvedItineraryItem = CollectionItineraryItem & {
		resolvedObject: Location | Transportation | Lodging | Note | Checklist | null;
	};

	// Group itinerary items by day
	type DayGroup = {
		date: string;
		displayDate: string;
		items: ResolvedItineraryItem[];
		overnightLodging: Lodging[]; // Lodging where guest is staying overnight (not check-in day)
	};

	$: days = groupItemsByDay(collection);
	$: unscheduledItems = getUnscheduledItems(collection);

	// Auto-generate state
	let isAutoGenerating = false;

	// Saving state for itinerary reorders. When true, disable drag interactions.
	let isSavingOrder = false;
	// Which day (ISO date string) is currently being saved. Used to show per-day spinner.
	let savingDay: string | null = null;

	// Check if auto-generate is available (only for users with modify permission)
	$: canAutoGenerate =
		canModify && collection.itinerary?.length === 0 && hasDatedRecords(collection);

	function hasDatedRecords(collection: Collection): boolean {
		// Check if collection has any dated records
		const hasVisits =
			collection.locations?.some((loc) => loc.visits?.some((v) => v.start_date)) || false;
		const hasLodging = collection.lodging?.some((l) => l.check_in) || false;
		const hasTransportation = collection.transportations?.some((t) => t.date) || false;
		const hasNotes = collection.notes?.some((n) => n.date) || false;
		const hasChecklists = collection.checklists?.some((c) => c.date) || false;

		return hasVisits || hasLodging || hasTransportation || hasNotes || hasChecklists;
	}

	async function handleAutoGenerate() {
		if (!canAutoGenerate || isAutoGenerating) return;

		isAutoGenerating = true;

		try {
			const response = await fetch('/api/itineraries/auto-generate/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					collection_id: collection.id
				})
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || error.error || 'Failed to auto-generate itinerary');
			}

			const data = await response.json();

			// Refresh the page to load the updated itinerary
			window.location.reload();
		} catch (error) {
			console.error('Auto-generate error:', error);
			alert(error.message || 'Failed to auto-generate itinerary');
			isAutoGenerating = false;
		}
	}

	function handleRemoveItineraryItem(event: CustomEvent<CollectionItineraryItem>) {
		const itemToRemove = event.detail;
		collection.itinerary = collection.itinerary?.filter((it) => it.id !== itemToRemove.id);
		days = groupItemsByDay(collection);
	}

	let locationToEdit: Location | null = null;
	let isLocationModalOpen: boolean = false;
	function handleEditLocation(event: CustomEvent<Location>) {
		locationToEdit = event.detail;
		isLocationModalOpen = true;
	}

	function handleDeleteLocation(event: CustomEvent<Location>) {
		// remove locally deleted location from itinerary view and list
		const deletedLocation = event.detail;
		collection.locations = collection.locations?.filter((loc) => loc.id !== deletedLocation.id);
		collection.itinerary = collection.itinerary?.filter(
			(it) => !(it.item?.type === 'location' && it.object_id === deletedLocation.id)
		);
	}

	let locationBeingUpdated: Location | null = null;

	let isLodgingModalOpen = false;
	let isTransportationModalOpen = false;
	let isNoteModalOpen = false;
	let isChecklistModalOpen = false;
	let isItineraryLinkModalOpen = false;

	// Store the target date and display date for the link modal
	let linkModalTargetDate: string = '';
	let linkModalDisplayDate: string = '';

	// When opening a "create new item" modal we store the target date here
	let pendingAddDate: string | null = null;

	// Sync the locationBeingUpdated with the collection.locations array
	$: if (locationBeingUpdated && locationBeingUpdated.id && collection) {
		// Make a shallow copy of locations (ensure array exists)
		const locs = collection.locations ? [...collection.locations] : [];

		const index = locs.findIndex((loc) => loc.id === locationBeingUpdated.id);

		if (index !== -1) {
			// Ensure visits are properly synced and replace the item immutably
			locs[index] = {
				...locs[index],
				...locationBeingUpdated,
				visits: locationBeingUpdated.visits || locs[index].visits || []
			};
		} else {
			// Prepend new/updated location
			locs.unshift({ ...locationBeingUpdated });
		}

		// Assign back to collection immutably to trigger reactivity
		collection = { ...collection, locations: locs };
	}

	// If a new location was just created and we have a pending add-date,
	// attach it to that date in the itinerary.
	$: if (locationBeingUpdated?.id && pendingAddDate) {
		addItineraryItemForObject('location', locationBeingUpdated.id, pendingAddDate);
		pendingAddDate = null;
	}

	/**
	 * Get lodging items where the guest is staying overnight on a given date
	 * (i.e., the date is between check_in and check_out, but NOT the check_in date itself)
	 */
	function getOvernightLodgingForDate(collection: Collection, dateISO: string): Lodging[] {
		if (!collection.lodging) return [];

		const targetDate = DateTime.fromISO(dateISO).startOf('day');

		// Helper: only include lodging that has been added to the itinerary
		function isLodgingScheduled(lodgingId: any): boolean {
			return !!collection.itinerary?.some((it) => {
				const objectType = it.item?.type || '';
				return objectType === 'lodging' && it.object_id === lodgingId;
			});
		}

		return collection.lodging.filter((lodging) => {
			// Only consider lodging entries that have both check-in and check-out
			if (!lodging.check_in || !lodging.check_out) return false;

			// Skip lodgings that are not scheduled in the itinerary
			if (!isLodgingScheduled(lodging.id)) return false;

			// Extract just the date portion (YYYY-MM-DD) to avoid timezone shifts
			const checkInDateStr = lodging.check_in.split('T')[0];
			const checkOutDateStr = lodging.check_out.split('T')[0];

			const checkIn = DateTime.fromISO(checkInDateStr).startOf('day');
			const checkOut = DateTime.fromISO(checkOutDateStr).startOf('day');

			// The guest is staying overnight if the target date is between
			// check-in (inclusive) and check-out (exclusive). This includes the
			// check-in night as requested.
			return targetDate >= checkIn && targetDate < checkOut;
		});
	}

	function resolveItineraryItem(
		item: CollectionItineraryItem,
		collection: Collection
	): ResolvedItineraryItem {
		let resolvedObject = null;

		// Resolve based on item.type which tells us the object type
		const objectType = item.item?.type || '';

		if (objectType === 'location') {
			// Find location by ID
			resolvedObject = collection.locations?.find((loc) => loc.id === item.object_id) || null;
		} else if (objectType === 'transportation') {
			resolvedObject = collection.transportations?.find((t) => t.id === item.object_id) || null;
		} else if (objectType === 'lodging') {
			resolvedObject = collection.lodging?.find((l) => l.id === item.object_id) || null;
		} else if (objectType === 'note') {
			resolvedObject = collection.notes?.find((n) => n.id === item.object_id) || null;
		} else if (objectType === 'checklist') {
			resolvedObject = collection.checklists?.find((c) => c.id === item.object_id) || null;
		}

		return {
			...item,
			resolvedObject
		};
	}

	function groupItemsByDay(collection: Collection): DayGroup[] {
		// Build a map of date -> resolved items from existing itinerary entries
		const grouped = new Map<string, ResolvedItineraryItem[]>();

		collection.itinerary?.forEach((item) => {
			if (item.date) {
				if (!grouped.has(item.date)) grouped.set(item.date, []);
				const resolved = resolveItineraryItem(item, collection);
				grouped.get(item.date)!.push(resolved);
			}
		});

		// Determine a date range to display. Prefer explicit collection start/end if present,
		// otherwise use min/max dates found in itinerary items. If no dates at all, return []
		let startDateISO: string | null = null;
		let endDateISO: string | null = null;

		if (collection.start_date && collection.end_date) {
			startDateISO = collection.start_date;
			endDateISO = collection.end_date;
		} else {
			// derive from itinerary dates if available
			const dates = Array.from(grouped.keys()).sort();
			if (dates.length > 0) {
				startDateISO = dates[0];
				endDateISO = dates[dates.length - 1];
			}
		}

		if (!startDateISO || !endDateISO) return [];

		const start = DateTime.fromISO(startDateISO).startOf('day');
		const end = DateTime.fromISO(endDateISO).startOf('day');

		const days: DayGroup[] = [];
		for (let dt = start; dt <= end; dt = dt.plus({ days: 1 })) {
			const iso = dt.toISODate();
			const items = (grouped.get(iso) || []).sort((a, b) => a.order - b.order);
			const overnightLodging = getOvernightLodgingForDate(collection, iso);
			days.push({
				date: iso,
				displayDate: dt.toFormat('cccc, LLLL d, yyyy'),
				items,
				overnightLodging
			});
		}

		return days;
	}

	function getUnscheduledItems(collection: Collection): any[] {
		// Get all items that are linked to collection but not in itinerary
		const scheduledIds = new Set(collection.itinerary?.map((item) => item.object_id) || []);

		const unscheduled: any[] = [];

		// Check locations
		collection.locations?.forEach((location) => {
			if (!scheduledIds.has(location.id)) {
				unscheduled.push({ type: 'location', item: location });
			}
		});

		// Check transportation
		collection.transportations?.forEach((transport) => {
			if (!scheduledIds.has(transport.id)) {
				unscheduled.push({ type: 'transportation', item: transport });
			}
		});

		// Check lodging
		collection.lodging?.forEach((lodge) => {
			if (!scheduledIds.has(lodge.id)) {
				unscheduled.push({ type: 'lodging', item: lodge });
			}
		});

		// Check notes
		collection.notes?.forEach((note) => {
			if (!scheduledIds.has(note.id)) {
				unscheduled.push({ type: 'note', item: note });
			}
		});

		// Check checklists
		collection.checklists?.forEach((checklist) => {
			if (!scheduledIds.has(checklist.id)) {
				unscheduled.push({ type: 'checklist', item: checklist });
			}
		});

		return unscheduled;
	}

	function isMultiDay(item: ResolvedItineraryItem): boolean {
		if (item.start_datetime && item.end_datetime) {
			const start = DateTime.fromISO(item.start_datetime);
			const end = DateTime.fromISO(item.end_datetime);
			return !start.hasSame(end, 'day');
		}
		return false;
	}

	function handleDndConsider(dayIndex: number, e: CustomEvent) {
		const { items: newItems } = e.detail;
		// Update the local state immediately for smooth drag feedback
		days[dayIndex].items = newItems;
		days = [...days];
	}

	async function handleDndFinalize(dayIndex: number, e: CustomEvent) {
		const { items: newItems, info } = e.detail;

		// Update local state
		days[dayIndex].items = newItems;
		days = [...days];

		// Save to backend if item was actually moved (not just considered)
		if (
			info.trigger === TRIGGERS.DROPPED_INTO_ZONE ||
			info.trigger === TRIGGERS.DROPPED_INTO_ANOTHER
		) {
			// Prevent further dragging while we persist the new order
			if (!isSavingOrder) {
				isSavingOrder = true;
				// mark this day as saving so we can show a spinner on that day's header
				savingDay = days[dayIndex]?.date || null;
				try {
					await saveReorderedItems();
				} finally {
					isSavingOrder = false;
					savingDay = null;
				}
			}
		}
	}

	async function saveReorderedItems() {
		try {
			// Collect all items across all days with their new positions
			const itemsToUpdate = days.flatMap((day) =>
				day.items
					.filter((item) => item.id && !item[SHADOW_ITEM_MARKER_PROPERTY_NAME])
					.map((item, index) => ({
						id: item.id,
						date: day.date,
						order: index
					}))
			);

			if (itemsToUpdate.length === 0) {
				return;
			}

			const response = await fetch('/api/itineraries/reorder/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					items: itemsToUpdate
				})
			});

			if (!response.ok) {
				throw new Error('Failed to save item order');
			}

			// Optionally show success feedback
			console.log('Itinerary order saved successfully');
			// Make sure to sync the collection.itinerary with the new order
			const updatedItinerary = collection.itinerary?.map((it) => {
				const updatedItem = itemsToUpdate.find((upd) => upd.id === it.id);
				if (updatedItem) {
					return {
						...it,
						date: updatedItem.date,
						order: updatedItem.order
					};
				}
				return it;
			});
			collection.itinerary = updatedItinerary;
		} catch (error) {
			console.error('Error saving itinerary order:', error);
			// Optionally show error notification to user
			alert('Failed to save itinerary order. Please try again.');
		}
	}

	// Add an itinerary item locally and attempt to persist to backend
	async function addItineraryItemForObject(
		objectType: string,
		objectId: string,
		dateISO: string,
		updateItemDate: boolean = false
	) {
		const tempId = `temp-${Date.now()}`;
		const day = days.find((d) => d.date === dateISO);
		const order = day ? day.items.length : 0;

		const newIt = {
			id: tempId,
			collection: collection.id,
			content_type: objectType,
			object_id: objectId,
			item: { id: objectId, type: objectType },
			date: dateISO,
			order,
			created_at: new Date().toISOString()
		};

		collection.itinerary = [...(collection.itinerary || []), newIt];
		days = groupItemsByDay(collection);

		try {
			const res = await fetch('/api/itineraries/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					collection: collection.id,
					content_type: objectType,
					object_id: objectId,
					date: dateISO,
					order,
					update_item_date: updateItemDate
				})
			});

			if (!res.ok) {
				const j = await res.json().catch(() => ({}));
				throw new Error(j.detail || 'Failed to add itinerary item');
			}

			const created = await res.json();
			collection.itinerary = collection.itinerary.map((it) => (it.id === tempId ? created : it));

			// If we updated the item's date, update local state directly
			if (updateItemDate) {
				const isoDate = `${dateISO}T00:00:00`;

				if (objectType === 'location') {
					// For locations, create a new visit locally
					if (collection.locations) {
						collection.locations = collection.locations.map((loc) => {
							if (loc.id === objectId) {
								const newVisit = {
									id: `temp-visit-${Date.now()}`,
									location: objectId,
									start_date: `${dateISO}T00:00:00`,
									end_date: `${dateISO}T23:59:59`,
									notes: 'Created from itinerary planning',
									created_at: new Date().toISOString(),
									updated_at: new Date().toISOString(),
									images: [],
									attachments: []
								};
								return {
									...loc,
									visits: [...(loc.visits || []), newVisit]
								};
							}
							return loc;
						});
					}
				} else if (objectType === 'transportation') {
					if (collection.transportations) {
						collection.transportations = collection.transportations.map((t) =>
							t.id === objectId ? { ...t, date: isoDate } : t
						);
					}
				} else if (objectType === 'lodging') {
					if (collection.lodging) {
						collection.lodging = collection.lodging.map((l) =>
							l.id === objectId ? { ...l, check_in: isoDate } : l
						);
					}
				} else if (objectType === 'note') {
					if (collection.notes) {
						collection.notes = collection.notes.map((n) =>
							n.id === objectId ? { ...n, date: isoDate } : n
						);
					}
				} else if (objectType === 'checklist') {
					if (collection.checklists) {
						collection.checklists = collection.checklists.map((c) =>
							c.id === objectId ? { ...c, date: isoDate } : c
						);
					}
				}
			}

			days = groupItemsByDay(collection);
		} catch (err) {
			console.error('Error creating itinerary item:', err);
			alert('Failed to add item to itinerary.');
			collection.itinerary = collection.itinerary.filter((it) => it.id !== tempId);
			days = groupItemsByDay(collection);
		}
	}
</script>

{#if isLocationModalOpen}
	<NewLocationModal
		on:close={() => (isLocationModalOpen = false)}
		{user}
		{locationToEdit}
		bind:location={locationBeingUpdated}
		{collection}
	/>
{/if}

{#if isLodgingModalOpen}
	<LodgingModal
		on:close={() => (isLodgingModalOpen = false)}
		{collection}
		on:save={(e) => {
			const lodging = e.detail;
			collection.lodging = [...(collection.lodging || []), lodging];
			if (pendingAddDate) {
				addItineraryItemForObject('lodging', lodging.id, pendingAddDate);
				pendingAddDate = null;
			}
			isLodgingModalOpen = false;
		}}
	/>
{/if}

{#if isTransportationModalOpen}
	<TransportationModal
		on:close={() => (isTransportationModalOpen = false)}
		{collection}
		on:save={(e) => {
			const transportation = e.detail;
			collection.transportations = [...(collection.transportations || []), transportation];
			if (pendingAddDate) {
				addItineraryItemForObject('transportation', transportation.id, pendingAddDate);
				pendingAddDate = null;
			}
			isTransportationModalOpen = false;
		}}
	/>
{/if}

{#if isNoteModalOpen}
	<NoteModal
		on:close={() => (isNoteModalOpen = false)}
		{collection}
		on:save={(e) => {
			const note = e.detail;
			collection.notes = [...(collection.notes || []), note];
			if (pendingAddDate) {
				addItineraryItemForObject('note', note.id, pendingAddDate);
				pendingAddDate = null;
			}
			isNoteModalOpen = false;
		}}
	/>
{/if}

{#if isChecklistModalOpen}
	<ChecklistModal
		on:close={() => (isChecklistModalOpen = false)}
		{collection}
		on:save={(e) => {
			const checklist = e.detail;
			collection.checklists = [...(collection.checklists || []), checklist];
			if (pendingAddDate) {
				addItineraryItemForObject('checklist', checklist.id, pendingAddDate);
				pendingAddDate = null;
			}
			isChecklistModalOpen = false;
		}}
	/>
{/if}

{#if isItineraryLinkModalOpen}
	<ItineraryLinkModal
		{collection}
		{user}
		targetDate={linkModalTargetDate}
		displayDate={linkModalDisplayDate}
		on:close={() => (isItineraryLinkModalOpen = false)}
		on:addItem={(e) => {
			const { type, itemId, updateDate } = e.detail;
			addItineraryItemForObject(type, itemId, linkModalTargetDate, updateDate);
		}}
	/>
{/if}

{#if canAutoGenerate}
	<div class="alert alert-info shadow-lg mb-6">
		<div class="flex-1 flex items-center gap-3 min-w-0">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				class="w-6 h-6 stroke-current flex-shrink-0"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
				></path>
			</svg>
			<div class="min-w-0">
				<div class="flex items-baseline gap-3">
					<h3 class="font-bold truncate">Auto-Generate Itinerary</h3>
				</div>
				<div class="text-sm opacity-90 truncate">
					This collection has dated items but no itinerary yet. Would you like to automatically
					organize them by date?
				</div>
			</div>
		</div>
		<div class="flex-none ml-3">
			<button
				class="btn btn-sm btn-primary"
				disabled={isAutoGenerating}
				on:click={handleAutoGenerate}
			>
				{#if isAutoGenerating}
					<span class="loading loading-spinner loading-sm"></span>
					Generating...
				{:else}
					Auto-Generate
				{/if}
			</button>
		</div>
	</div>
{/if}

{#if days.length === 0 && unscheduledItems.length === 0}
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body text-center py-12">
			<CalendarBlank class="w-16 h-16 mx-auto mb-4 opacity-50" />
			<h3 class="text-2xl font-bold mb-2">No Itinerary Yet</h3>
			<p class="opacity-70">Start planning your trip by adding items to specific days.</p>
		</div>
	</div>
{:else}
	<div class="space-y-6">
		<!-- Scheduled Days -->
		{#each days as day, dayIndex}
			{@const dayNumber = dayIndex + 1}
			{@const totalDays = days.length}
			{@const weekday = DateTime.fromISO(day.date).toFormat('ccc')}
			{@const dayOfMonth = DateTime.fromISO(day.date).toFormat('d')}
			{@const monthAbbrev = DateTime.fromISO(day.date).toFormat('LLL')}

			<div class="card bg-base-200 shadow-xl">
				<div class="card-body">
					<!-- Day Header (compact, shows date pill + Day X of Y + items + add/save) -->

					<div class="flex items-start gap-4 mb-4 pb-4 border-b border-base-300">
						<!-- Date pill -->
						<div class="flex-none">
							<div class="text-center bg-base-300 rounded-lg px-3 py-2 w-20">
								<div class="text-xs opacity-70">{weekday}</div>
								<div class="text-2xl font-bold -mt-1">{dayOfMonth}</div>
								<div class="text-xs opacity-70">{monthAbbrev}</div>
							</div>
						</div>

						<!-- Title and meta -->
						<div class="flex-1 min-w-0">
							<h3 class="text-lg md:text-xl font-bold truncate">{day.displayDate}</h3>
							<div class="text-sm opacity-70 mt-1 flex items-center gap-3">
								<span class="font-medium">Day {dayNumber} of {totalDays}</span>
								<span class="opacity-50">•</span>
								<span>{day.items.length} {day.items.length === 1 ? 'item' : 'items'}</span>
								{#if day.overnightLodging.length > 0}
									<span class="badge badge-info badge-outline">Overnight Lodging</span>
								{/if}
							</div>
						</div>

						<!-- Actions: saving indicator + Add dropdown -->
						<div class="flex-none ml-3 flex items-start gap-2">
							{#if savingDay === day.date}
								<div>
									<div class="badge badge-neutral-300 gap-2 p-2">
										<span class="loading loading-spinner loading-sm"></span>
										Saving...
									</div>
								</div>
							{/if}

							{#if canModify}
								<div class="dropdown z-[9999]">
									<label tabindex="0" class="btn btn-sm btn-outline gap-2">Add</label>
									<ul
										tabindex="0"
										class="dropdown-content menu p-2 shadow bg-base-300 rounded-box w-56"
									>
										<li>
											<a
												on:click={() => {
													linkModalTargetDate = day.date;
													linkModalDisplayDate = day.displayDate;
													isItineraryLinkModalOpen = true;
												}}>Link existing item</a
											>
										</li>
										<li class="menu-title">Create new</li>
										<li>
											<a
												on:click={() => {
													pendingAddDate = day.date;
													isLocationModalOpen = true;
												}}>Location</a
											>
										</li>
										<li>
											<a
												on:click={() => {
													pendingAddDate = day.date;
													isLodgingModalOpen = true;
												}}>Lodging</a
											>
										</li>
										<li>
											<a
												on:click={() => {
													pendingAddDate = day.date;
													isTransportationModalOpen = true;
												}}>Transportation</a
											>
										</li>
										<li>
											<a
												on:click={() => {
													pendingAddDate = day.date;
													isNoteModalOpen = true;
												}}>Note</a
											>
										</li>
										<li>
											<a
												on:click={() => {
													pendingAddDate = day.date;
													isChecklistModalOpen = true;
												}}>Checklist</a
											>
										</li>
									</ul>
								</div>
							{/if}
						</div>
					</div>

					<!-- Day Items -->
					<div>
						{#if day.items.length === 0}
							<div
								class="card bg-base-100 shadow-sm border border-dashed border-base-300 p-4 text-center"
							>
								<div class="card-body p-2">
									<CalendarBlank class="w-8 h-8 mx-auto mb-2 opacity-40" />
									<p class="opacity-70">No plans for this day</p>
								</div>
							</div>
						{:else}
							<div
								use:dndzone={{
									items: day.items,
									flipDurationMs,
									dropTargetStyle: { outline: 'none', border: 'none' },
									dragDisabled: isSavingOrder || !canModify,
									dropFromOthersDisabled: true
								}}
								on:consider={(e) => handleDndConsider(dayIndex, e)}
								on:finalize={(e) => handleDndFinalize(dayIndex, e)}
								class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"
							>
								{#each day.items as item, index (item.id)}
									{@const objectType = item.item?.type || ''}
									{@const resolvedObj = item.resolvedObject}
									{@const multiDay = isMultiDay(item)}
									{@const isDraggingShadow = item[SHADOW_ITEM_MARKER_PROPERTY_NAME]}

									<div
										class="group relative transition-all duration-200 pointer-events-auto h-full {isDraggingShadow
											? 'opacity-40 scale-95'
											: 'hover:shadow-lg'}"
										animate:flip={{ duration: flipDurationMs }}
									>
										{#if resolvedObj}
											<!-- Drag Handle Container -->
											{#if canModify}
												<div
													class="absolute left-2 top-2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
													title="Drag to reorder"
												>
													<div
														class="itinerary-drag-handle btn btn-circle btn-xs btn-ghost bg-base-100/80 backdrop-blur-sm shadow-sm hover:bg-base-200 cursor-grab active:cursor-grabbing"
														aria-label="Drag to reorder"
														role="button"
														tabindex="0"
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															class="h-3 w-3"
															fill="none"
															viewBox="0 0 24 24"
															stroke="currentColor"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M4 8h16M4 16h16"
															/>
														</svg>
													</div>
												</div>
											{/if}

											<!-- Order Badge
											<div class="absolute right-2 top-2 z-10">
												<div
													class="badge badge-primary badge-sm font-bold shadow-md"
													title="Item order"
												>
													#{index + 1}
												</div>
											</div> -->

											<!-- Multi-day indicator for lodging -->
											{#if multiDay && objectType === 'lodging'}
												<div class="absolute left-2 bottom-2 z-10">
													<div class="badge badge-info badge-xs gap-1 shadow-sm">
														<svg
															xmlns="http://www.w3.org/2000/svg"
															class="h-3 w-3"
															fill="none"
															viewBox="0 0 24 24"
															stroke="currentColor"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
															/>
														</svg>
														Multi-day
													</div>
												</div>
											{/if}

											<!-- Card with smooth transition and proper sizing for grid -->
											<div class="transition-all duration-200 h-full">
												<!-- Display the appropriate card based on type -->
												{#if objectType === 'location'}
													<LocationCard
														adventure={resolvedObj}
														on:edit={handleEditLocation}
														on:delete={handleDeleteLocation}
														itineraryItem={item}
														on:removeFromItinerary={handleRemoveItineraryItem}
														{user}
														{collection}
														compact={true}
													/>
												{:else if objectType === 'transportation'}
													<TransportationCard transportation={resolvedObj} {user} {collection} />
												{:else if objectType === 'lodging'}
													<LodgingCard lodging={resolvedObj} {user} {collection} />
												{:else if objectType === 'note'}
													<!-- @ts-ignore - TypeScript can't narrow union type properly -->
													<NoteCard note={resolvedObj} {user} {collection} />
												{:else if objectType === 'checklist'}
													<!-- @ts-ignore - TypeScript can't narrow union type properly -->
													<ChecklistCard checklist={resolvedObj} {user} {collection} />
												{/if}
											</div>
										{:else}
											<!-- Fallback for unresolved items -->
											<div class="alert alert-warning">
												<span>⚠️ Item not found (ID: {item.object_id})</span>
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<!-- Overnight Lodging Indicator -->
					{#if day.overnightLodging.length > 0}
						<div class="mt-4 pt-4 border-t border-base-300 border-dashed">
							<div class="flex items-center gap-2 mb-2 opacity-70">
								<Bed class="w-4 h-4" />
								<span class="text-sm font-medium">Staying overnight</span>
							</div>
							<div class="space-y-2">
								{#each day.overnightLodging as lodging}
									{@const checkOut = lodging.check_out
										? DateTime.fromISO(lodging.check_out.split('T')[0]).toFormat('LLL d')
										: null}
									<div
										class="flex items-center gap-3 bg-base-100 rounded-lg px-4 py-3 border border-base-300"
									>
										<div
											class="flex items-center justify-center w-8 h-8 rounded-full bg-info/20 text-info"
										>
											<Bed class="w-4 h-4" />
										</div>
										<div class="flex-1 min-w-0">
											<p class="font-medium truncate">{lodging.name}</p>
											{#if lodging.location}
												<p class="text-xs opacity-60 truncate">{lodging.location}</p>
											{/if}
										</div>
										{#if checkOut}
											<div class="badge badge-ghost badge-sm">
												Check-out: {checkOut}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/each}

		<!-- Unscheduled Items -->
		{#if unscheduledItems.length > 0}
			<div class="card bg-base-200 shadow-xl border-2 border-dashed border-base-300">
				<div class="card-body">
					<!-- Unscheduled Header -->
					<div class="flex items-center gap-3 mb-4 pb-4 border-b border-base-300">
						<div class="w-6 h-6 rounded-full border-2 border-dashed border-base-content/30"></div>
						<h3 class="text-xl font-bold opacity-70">Unscheduled Items</h3>
						<div class="badge badge-ghost ml-auto">
							{unscheduledItems.length}
							{unscheduledItems.length === 1 ? 'item' : 'items'}
						</div>
					</div>

					<p class="text-sm opacity-70 mb-4">
						These items are linked to this trip but haven't been added to a specific day yet.
					</p>

					<!-- Unscheduled Items List -->
					<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
						{#each unscheduledItems as { type, item }}
							<div class="relative opacity-60 hover:opacity-100 transition-opacity h-full">
								<!-- "Add to itinerary" indicator -->
								{#if canModify}
									<div class="absolute -right-2 top-2 z-10">
										<button class="btn btn-circle btn-sm btn-primary" title="Add to itinerary">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 4v16m8-8H4"
												/>
											</svg>
										</button>
									</div>
								{/if}

								<!-- Display the appropriate card -->
								{#if type === 'location'}
									<LocationCard adventure={item} {user} collection={null} />
								{:else if type === 'transportation'}
									<TransportationCard transportation={item} {user} {collection} />
								{:else if type === 'lodging'}
									<LodgingCard lodging={item} {user} {collection} />
								{:else if type === 'note'}
									<NoteCard note={item} {user} {collection} />
								{:else if type === 'checklist'}
									<ChecklistCard checklist={item} {user} {collection} />
								{/if}
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}
