<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import type { Collection, Note, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { marked } from 'marked'; // Import the markdown parser

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';
	import DeleteWarning from './DeleteWarning.svelte';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import LinkVariant from '~icons/mdi/link-variant';

	export let note: Note;
	export let user: User | null = null;
	export let collection: Collection | null = null;
	export let readOnly: boolean = false;

	let isWarningModalOpen: boolean = false;

	function editNote() {
		dispatch('edit', note);
	}

	async function deleteNote() {
		const res = await fetch(`/api/notes/${note.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('success', $t('notes.note_deleted'));
			isWarningModalOpen = false;
			dispatch('delete', note.id);
		} else {
			addToast($t('notes.note_delete_error'), 'error');
		}
	}
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_note')}
		button_text="Delete"
		description={$t('adventures.note_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteNote}
	/>
{/if}

<div
	class="card w-full max-w-md bg-base-300 shadow hover:shadow-md transition-all duration-200 border border-base-300 group"
	aria-label="note-card"
>
	<div class="card-body p-4 space-y-3">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<div class="flex-1 min-w-0">
				<h2 class="text-lg font-semibold line-clamp-2">{note.name}</h2>
				<div class="flex flex-wrap items-center gap-2 mt-2">
					<div class="badge badge-primary badge-sm">{$t('adventures.note')}</div>
				</div>
			</div>

			{#if !readOnly && (note.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid)))}
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
							<button on:click={editNote} class="flex items-center gap-2">
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

		<!-- Note Content Preview -->
		{#if note.content && note.content?.length > 0}
			<article
				class="prose prose-sm max-w-none overflow-hidden max-h-32 text-sm text-base-content/70 line-clamp-4"
			>
				{@html renderMarkdown(note.content || '')}
			</article>
		{/if}

		<!-- Inline Stats -->
		<div class="flex flex-wrap items-center gap-3 text-sm text-base-content/70">
			{#if note.date && note.date !== ''}
				<div class="flex items-center gap-1">
					<Calendar class="w-4 h-4 text-primary" />
					<span>{new Date(note.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}</span>
				</div>
			{/if}

			{#if note.links && note.links?.length > 0}
				<div class="badge badge-ghost badge-sm">
					<LinkVariant class="w-3 h-3 mr-1" />
					{note.links.length}
					{note.links.length > 1 ? $t('adventures.links') : $t('adventures.link')}
				</div>
			{/if}
		</div>

		<!-- Links Preview (compact) -->
		{#if note.links && note.links?.length > 0}
			<div class="flex flex-wrap gap-2">
				{#each note.links.slice(0, 2) as link}
					<a
						class="badge badge-outline badge-sm hover:badge-primary transition-colors"
						href={link}
						target="_blank"
						rel="noopener noreferrer"
					>
						<LinkVariant class="w-3 h-3 mr-1" />
						{link.split('//')[1]?.split('/', 1)[0]}
					</a>
				{/each}
				{#if note.links.length > 2}
					<span class="badge badge-ghost badge-sm">+{note.links.length - 2}</span>
				{/if}
			</div>
		{/if}
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

	.line-clamp-4 {
		display: -webkit-box;
		-webkit-line-clamp: 4;
		line-clamp: 4;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
