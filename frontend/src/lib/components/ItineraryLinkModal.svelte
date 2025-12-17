<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Collection, Location, Transportation, Lodging, Note, Checklist } from '$lib/types';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import CalendarBlank from '~icons/mdi/calendar-blank';
	import Clear from '~icons/mdi/close';
	import Link from '~icons/mdi/link-variant';
	import LocationCard from '$lib/components/LocationCard.svelte';
	import TransportationCard from '$lib/components/TransportationCard.svelte';
	import LodgingCard from '$lib/components/LodgingCard.svelte';
	import NoteCard from '$lib/components/NoteCard.svelte';
	import ChecklistCard from '$lib/components/ChecklistCard.svelte';
	import { t } from 'svelte-i18n';

	const dispatch = createEventDispatcher();

	export let collection: Collection;
	export let user: any;
	export let targetDate: string; // ISO date string
	export let displayDate: string; // Formatted display date

	let modal: HTMLDialogElement;

	// Group items into several categories so we can show:
	// - items already scheduled on this day
	// - unscheduled items that match this day (e.g. via visits/date)
	// - items already scheduled on other days
	// - unscheduled items on other days
	type GroupedItems = {
		scheduledOnThisDay: Array<{ type: string; item: any; dates?: string[] }>;
		onThisDay: Array<{ type: string; item: any }>;
		scheduledOtherDays: Array<{ type: string; item: any; dates?: string[] }>;
		otherDays: Array<{ type: string; item: any }>;
	};

	$: groupedItems = getUnscheduledItemsForDate(collection, targetDate);

	function getUnscheduledItemsForDate(collection: Collection, targetDate: string): GroupedItems {
		const itinerary = collection.itinerary || [];
		const scheduledMap = new Map<string, string[]>();
		itinerary.forEach((it) => {
			const id = it.object_id;
			const date = it.date || null;
			if (!scheduledMap.has(id)) scheduledMap.set(id, []);
			if (date) scheduledMap.get(id)!.push(date);
		});

		const scheduledOnThisDay: any[] = [];
		const scheduledOtherDays: any[] = [];
		const onThisDay: any[] = [];
		const otherDays: any[] = [];

		// Helper to check scheduled status
		function isScheduled(id: string) {
			return scheduledMap.has(id);
		}

		// Process locations
		collection.locations?.forEach((location) => {
			if (isScheduled(location.id)) {
				const dates = scheduledMap.get(location.id) || [];
				if (dates.includes(targetDate)) {
					scheduledOnThisDay.push({ type: 'location', item: location, dates });
				} else {
					scheduledOtherDays.push({ type: 'location', item: location, dates });
				}
			} else {
				// Unsheduled: check visits for the target date
				const hasVisitOnDate = location.visits?.some((visit) => {
					if (!visit.start_date) return false;
					const visitDate = visit.start_date.split('T')[0];
					return visitDate === targetDate;
				});

				if (hasVisitOnDate) onThisDay.push({ type: 'location', item: location });
				else otherDays.push({ type: 'location', item: location });
			}
		});

		// Process transportations
		collection.transportations?.forEach((transport) => {
			if (isScheduled(transport.id)) {
				const dates = scheduledMap.get(transport.id) || [];
				if (dates.includes(targetDate))
					scheduledOnThisDay.push({ type: 'transportation', item: transport, dates });
				else scheduledOtherDays.push({ type: 'transportation', item: transport, dates });
			} else {
				const itemDate = transport.date ? transport.date.split('T')[0] : null;
				if (itemDate === targetDate) onThisDay.push({ type: 'transportation', item: transport });
				else otherDays.push({ type: 'transportation', item: transport });
			}
		});

		// Process lodging
		collection.lodging?.forEach((lodge) => {
			if (isScheduled(lodge.id)) {
				const dates = scheduledMap.get(lodge.id) || [];
				if (dates.includes(targetDate))
					scheduledOnThisDay.push({ type: 'lodging', item: lodge, dates });
				else scheduledOtherDays.push({ type: 'lodging', item: lodge, dates });
			} else {
				const itemDate = lodge.check_in ? lodge.check_in.split('T')[0] : null;
				if (itemDate === targetDate) onThisDay.push({ type: 'lodging', item: lodge });
				else otherDays.push({ type: 'lodging', item: lodge });
			}
		});

		// Process notes
		collection.notes?.forEach((note) => {
			if (isScheduled(note.id)) {
				const dates = scheduledMap.get(note.id) || [];
				if (dates.includes(targetDate))
					scheduledOnThisDay.push({ type: 'note', item: note, dates });
				else scheduledOtherDays.push({ type: 'note', item: note, dates });
			} else {
				otherDays.push({ type: 'note', item: note });
			}
		});

		// Process checklists
		collection.checklists?.forEach((checklist) => {
			if (isScheduled(checklist.id)) {
				const dates = scheduledMap.get(checklist.id) || [];
				if (dates.includes(targetDate))
					scheduledOnThisDay.push({ type: 'checklist', item: checklist, dates });
				else scheduledOtherDays.push({ type: 'checklist', item: checklist, dates });
			} else {
				otherDays.push({ type: 'checklist', item: checklist });
			}
		});

		return { scheduledOnThisDay, onThisDay, scheduledOtherDays, otherDays };
	}

	onMount(() => {
		modal = document.getElementById('itinerary_link_modal') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	function handleAddItem(type: string, itemId: string, updateDate: boolean) {
		dispatch('addItem', { type, itemId, updateDate });
		close();
	}
</script>

<dialog id="itinerary_link_modal" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
		<div
			class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<CalendarBlank class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							Link Items to {displayDate}
						</h1>
						<p class="text-sm text-base-content/60">
							{groupedItems.scheduledOnThisDay.length +
								groupedItems.onThisDay.length +
								groupedItems.scheduledOtherDays.length +
								groupedItems.otherDays.length}
							items available to link
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<Clear class="w-5 h-5" />
				</button>
			</div>
		</div>

		<div class="px-6">
			<!-- Items on this day -->
			{#if groupedItems.onThisDay.length > 0}
				<div class="mb-6">
					<h4 class="text-lg font-semibold mb-3 flex items-center gap-2">
						<CalendarBlank class="w-5 h-5 text-primary" />
						Items on this day
					</h4>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						{#each groupedItems.onThisDay as { type, item }}
							<div class="card bg-base-100 border border-base-300 shadow-sm">
								<div class="card-body p-4">
									<div class="mb-3">
										{#if type === 'location'}
											<LocationCard adventure={item} {user} {collection} compact={true} />
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
									<button
										class="btn btn-primary btn-sm w-full"
										on:click={() => handleAddItem(type, item.id, false)}
									>
										Add to Itinerary
									</button>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if groupedItems.scheduledOnThisDay.length > 0}
				<div class="mb-6">
					<h4 class="text-lg font-semibold mb-3 flex items-center gap-2">
						<CalendarBlank class="w-5 h-5 text-primary" />
						Already added on this day
					</h4>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						{#each groupedItems.scheduledOnThisDay as { type, item, dates }}
							<div class="card bg-base-100 border border-base-300 shadow-sm">
								<div class="card-body p-4">
									<div class="mb-3">
										{#if type === 'location'}
											<LocationCard adventure={item} {user} {collection} compact={true} />
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
									<div class="text-sm opacity-70 mb-2">Already on: {(dates || []).join(', ')}</div>
									<div class="text-xs opacity-50">
										Use "Items on other days" or "Add as is" to duplicate onto this date.
									</div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if groupedItems.onThisDay.length > 0 && groupedItems.otherDays.length > 0}
				<div class="divider"></div>
			{/if}

			{#if groupedItems.scheduledOtherDays.length > 0}
				<div class="mb-6">
					<h4 class="text-lg font-semibold mb-3 opacity-70">Already added on other days</h4>
					<p class="text-sm opacity-60 mb-4">
						These items are already in your itinerary on a different date — you can add them again
						to this day or update their date.
					</p>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						{#each groupedItems.scheduledOtherDays as { type, item, dates }}
							<div class="card bg-base-100 border border-base-300 shadow-sm">
								<div class="card-body p-4">
									<div class="mb-3">
										{#if type === 'location'}
											<LocationCard adventure={item} {user} {collection} compact={true} />
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
									<div class="text-sm opacity-70 mb-2">On: {(dates || []).join(', ')}</div>
									<div class="flex gap-2">
										<button
											class="btn btn-outline btn-sm flex-1"
											on:click={() => handleAddItem(type, item.id, false)}>Add to This Day</button
										>
										<button
											class="btn btn-primary btn-sm flex-1"
											on:click={() => handleAddItem(type, item.id, true)}>Add & Update Date</button
										>
									</div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Items on other days -->
			{#if groupedItems.otherDays.length > 0}
				<div class="mb-6">
					<h4 class="text-lg font-semibold mb-3 opacity-70">Items on other days</h4>
					<p class="text-sm opacity-60 mb-4">
						These items have different dates. You can add them and optionally update their date to
						match.
					</p>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						{#each groupedItems.otherDays as { type, item }}
							<div class="card bg-base-100 border border-base-300 shadow-sm">
								<div class="card-body p-4">
									<div class="mb-3">
										{#if type === 'location'}
											<LocationCard adventure={item} {user} {collection} compact={true} />
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
									<div class="flex gap-2">
										<button
											class="btn btn-outline btn-sm flex-1"
											on:click={() => handleAddItem(type, item.id, false)}
										>
											Add as is
										</button>
										<button
											class="btn btn-primary btn-sm flex-1"
											on:click={() => handleAddItem(type, item.id, true)}
										>
											Add & Update Date
										</button>
									</div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if groupedItems.scheduledOnThisDay.length + groupedItems.onThisDay.length + groupedItems.scheduledOtherDays.length + groupedItems.otherDays.length === 0}
				<div class="card bg-base-200">
					<div class="card-body text-center py-12">
						<CalendarBlank class="w-16 h-16 mx-auto mb-4 opacity-30" />
						<p class="text-lg font-semibold opacity-70">No unscheduled items available</p>
						<p class="text-sm opacity-60 mt-2">
							All items have been added to the itinerary or there are no items to add.
						</p>
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer Actions -->
		<div
			class="sticky bottom-0 bg-base-100/90 backdrop-blur-lg border-t border-base-300 -mx-6 -mb-6 px-6 py-4 mt-6"
		>
			<div class="flex items-center justify-between">
				<div class="text-sm text-base-content/60">
					{groupedItems.scheduledOnThisDay.length +
						groupedItems.onThisDay.length +
						groupedItems.scheduledOtherDays.length +
						groupedItems.otherDays.length} items available to link
				</div>
				<button class="btn btn-primary gap-2" on:click={close}>
					<Link class="w-4 h-4" />
					{$t('adventures.done')}
				</button>
			</div>
		</div>
	</div>
</dialog>
