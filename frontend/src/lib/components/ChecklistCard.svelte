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
	import { isEntityOutsideCollectionDateRange } from '$lib/dateUtils';

	export let checklist: Checklist;
	export let user: User | null = null;
	export let collection: Collection;

	let isWarningModalOpen: boolean = false;

	let outsideCollectionRange: boolean = false;

	$: {
		outsideCollectionRange = isEntityOutsideCollectionDateRange(checklist, collection);
	}

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
					{#if outsideCollectionRange}
						<div class="badge badge-error badge-xs">{$t('adventures.out_of_range')}</div>
					{/if}
				</div>
			</div>

			{#if checklist.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
				<div class="dropdown dropdown-end">
					<div tabindex="0" role="button" class="btn btn-square btn-sm p-1 text-base-content">
						<DotsHorizontal class="w-5 h-5" />
					</div>
					<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
					<ul
						tabindex="0"
						class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow-lg border border-base-300"
					>
						<li>
							<button on:click={editChecklist} class="flex items-center gap-2">
								<FileDocumentEdit class="w-4 h-4" />
								{$t('notes.open')}
							</button>
						</li>
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
				</div>
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
