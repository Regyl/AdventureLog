<script lang="ts">
	import { addToast } from '$lib/toasts';
	import type { Checklist, Collection, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	import Launch from '~icons/mdi/launch';
	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';
	import DeleteWarning from './DeleteWarning.svelte';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import CheckCircle from '~icons/mdi/check-circle';
	import CheckboxBlankCircleOutline from '~icons/mdi/checkbox-blank-circle-outline';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import type { CollectionItineraryItem } from '$lib/types';

	export let checklist: Checklist;
	export let user: User | null = null;
	export let collection: Collection;
	export let readOnly: boolean = false;
	export let itineraryItem: CollectionItineraryItem | null = null;

	let isWarningModalOpen: boolean = false;

	function editChecklist() {
		dispatch('edit', checklist);
	}

	async function deleteChecklist() {
		const res = await fetch(`/api/checklists/${checklist.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('success', $t('checklist.checklist_deleted'));
			isWarningModalOpen = false;
			dispatch('delete', checklist.id);
		} else {
			addToast($t('checklist.checklist_delete_error'), 'error');
		}
	}

	async function removeFromItinerary() {
		let itineraryItemId = itineraryItem?.id;
		let res = await fetch(`/api/itineraries/${itineraryItemId}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('info', $t('itinerary.item_remove_success'));
			dispatch('removeFromItinerary', itineraryItem);
		} else {
			addToast('error', $t('itinerary.item_remove_error'));
		}
	}
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_checklist')}
		button_text="Delete"
		description={$t('adventures.checklist_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteChecklist}
	/>
{/if}
<div
	class="card w-full max-w-md bg-base-300 shadow hover:shadow-md transition-all duration-200 border border-base-300 group"
	aria-label="checklist-card"
>
	<div class="card-body p-4 space-y-3">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<div class="flex-1 min-w-0">
				<h2 class="text-lg font-semibold line-clamp-2">{checklist.name}</h2>
				<div class="flex flex-wrap items-center gap-2 mt-2">
					<div class="badge badge-primary badge-sm">{$t('adventures.checklist')}</div>
				</div>
			</div>

			{#if !readOnly && (checklist.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid)))}
				<details class="dropdown dropdown-end relative z-50">
					<summary class="btn btn-square btn-sm p-1 text-base-content">
						<DotsHorizontal class="w-5 h-5" />
					</summary>
					<ul
						class="dropdown-content menu bg-base-100 rounded-box z-[9999] w-52 p-2 shadow-lg border border-base-300"
					>
						<li>
							<button on:click={editChecklist} class="flex items-center gap-2">
								<FileDocumentEdit class="w-4 h-4" />
								{$t('notes.open')}
							</button>
						</li>
						{#if itineraryItem && itineraryItem.id}
							<div class="divider my-1"></div>
							<li>
								<button
									on:click={() => removeFromItinerary()}
									class="text-error flex items-center gap-2"
								>
									<CalendarRemove class="w-4 h-4 text-error" />
									{$t('itinerary.remove_from_itinerary')}
								</button>
							</li>
						{/if}
						<div class="divider my-1"></div>
						<li>
							<button
								class="text-error flex items-center gap-2"
								on:click={() => (isWarningModalOpen = true)}
							>
								<TrashCan class="w-4 h-4" />
								{$t('adventures.delete')}
							</button>
						</li>
					</ul>
				</details>
			{/if}
		</div>

		<!-- Checklist Items Preview -->
		{#if checklist.items.length > 0}
			<div class="space-y-2">
				{#each checklist.items.slice(0, 3) as item}
					<div class="flex items-center gap-2 text-sm text-base-content/70">
						{#if item.is_checked}
							<CheckCircle class="w-4 h-4 text-success flex-shrink-0" />
						{:else}
							<CheckboxBlankCircleOutline class="w-4 h-4 flex-shrink-0" />
						{/if}
						<span
							class="truncate"
							class:line-through={item.is_checked}
							class:opacity-60={item.is_checked}
						>
							{item.name}
						</span>
					</div>
				{/each}
				{#if checklist.items.length > 3}
					<div class="text-sm text-base-content/60 pl-6">
						+{checklist.items.length - 3}
						{$t('checklist.more_items')}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Inline Stats -->
		<div class="flex flex-wrap items-center gap-3 text-sm text-base-content/70">
			{#if checklist.date && checklist.date !== ''}
				<div class="flex items-center gap-1">
					<Calendar class="w-4 h-4 text-primary" />
					<span>{new Date(checklist.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}</span>
				</div>
			{/if}

			{#if checklist.items.length > 0}
				{@const completedCount = checklist.items.filter((item) => item.is_checked).length}
				<div class="badge badge-ghost badge-sm">
					{completedCount}/{checklist.items.length}
					{$t('checklist.completed')}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
