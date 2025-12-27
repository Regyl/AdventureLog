<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Collection, Transportation } from '$lib/types';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	import MarkdownEditor from './MarkdownEditor.svelte';

	// Icons
	import CollectionIcon from '~icons/mdi/folder-multiple';
	import InfoIcon from '~icons/mdi/information';
	import CalendarIcon from '~icons/mdi/calendar';
	import LinkIcon from '~icons/mdi/link';
	import SaveIcon from '~icons/mdi/content-save';
	import CloseIcon from '~icons/mdi/close';

	export let collectionToEdit: Collection | null = null;

	let collection: Collection = {
		id: collectionToEdit?.id || '',
		name: collectionToEdit?.name || '',
		description: collectionToEdit?.description || '',
		start_date: collectionToEdit?.start_date || null,
		end_date: collectionToEdit?.end_date || null,
		user: collectionToEdit?.user || '',
		is_public: collectionToEdit?.is_public || false,
		locations: collectionToEdit?.locations || [],
		link: collectionToEdit?.link || '',
		shared_with: undefined,
		itinerary: [],
		status: 'folder',
		days_until_start: null
	};

	console.log(collection);

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
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

	async function handleSubmit(event: Event) {
		event.preventDefault();
		console.log(collection);

		if (collection.start_date && !collection.end_date) {
			collection.end_date = collection.start_date;
		}

		if (
			collection.start_date &&
			collection.end_date &&
			collection.start_date > collection.end_date
		) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}

		if (!collection.start_date && collection.end_date) {
			collection.start_date = collection.end_date;
		}

		if (!collection.start_date && !collection.end_date) {
			collection.start_date = null;
			collection.end_date = null;
		}

		if (collection.id === '') {
			let res = await fetch('/api/collections', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(collection)
			});
			let data = await res.json();
			if (data.id) {
				collection = data as Collection;
				addToast('success', $t('collection.collection_created'));
				dispatch('save', collection);
			} else {
				console.error(data);
				addToast('error', $t('collection.error_creating_collection'));
			}
		} else {
			let res = await fetch(`/api/collections/${collection.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(collection)
			});
			let data = await res.json();
			if (data.id) {
				collection = data as Collection;
				addToast('success', $t('collection.collection_edit_success'));
				dispatch('save', collection);
			} else {
				addToast('error', $t('collection.error_editing_collection'));
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl max-h-[85vh] flex flex-col"
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
						<CollectionIcon class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{collectionToEdit
								? $t('adventures.edit_collection')
								: $t('collection.new_collection')}
						</h1>
						<p class="text-sm text-base-content/60">
							{collectionToEdit
								? $t('collection.update_collection_details')
								: $t('collection.create_new_collection')}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<CloseIcon class="w-5 h-5" />
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="p-6 overflow-auto max-h-[70vh]">
			<form method="post" on:submit={handleSubmit} class="space-y-6">
				<!-- Basic Information Section -->
				<div class="card bg-base-100 border border-base-300 shadow-lg">
					<div class="card-body p-6">
						<div class="flex items-center gap-3 mb-6">
							<div class="p-2 bg-primary/10 rounded-lg">
								<InfoIcon class="w-5 h-5 text-primary" />
							</div>
							<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
						</div>

						<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
							<!-- Left Column -->
							<div class="space-y-4">
								<!-- Name Field -->
								<div class="form-control">
									<label class="label" for="name">
										<span class="label-text font-medium"
											>{$t('adventures.name')}<span class="text-error ml-1">*</span></span
										>
									</label>
									<input
										type="text"
										id="name"
										name="name"
										bind:value={collection.name}
										class="input input-bordered w-full"
										placeholder={$t('collection.enter_collection_name')}
										required
									/>
								</div>

								<!-- Description Field -->
								<div class="form-control">
									<label class="label" for="description">
										<span class="label-text font-medium">{$t('adventures.description')}</span>
									</label>
									<MarkdownEditor bind:text={collection.description} editor_height={'h-32'} />
								</div>

								<!-- Link Field -->
								<div class="form-control">
									<label class="label" for="link">
										<span class="label-text font-medium flex items-center gap-2">
											<LinkIcon class="w-4 h-4" />
											{$t('adventures.link')}
										</span>
									</label>
									<input
										type="text"
										id="link"
										name="link"
										bind:value={collection.link}
										class="input input-bordered w-full"
										placeholder="https://example.com"
									/>
								</div>
							</div>

							<!-- Right Column -->
							<div class="space-y-4">
								<!-- Start Date -->
								<div class="form-control">
									<label class="label" for="start_date">
										<span class="label-text font-medium flex items-center gap-2">
											<CalendarIcon class="w-4 h-4" />
											{$t('adventures.start_date')}
										</span>
									</label>
									<input
										type="date"
										id="start_date"
										name="start_date"
										bind:value={collection.start_date}
										class="input input-bordered w-full"
									/>
								</div>

								<!-- End Date -->
								<div class="form-control">
									<label class="label" for="end_date">
										<span class="label-text font-medium flex items-center gap-2">
											<CalendarIcon class="w-4 h-4" />
											{$t('adventures.end_date')}
										</span>
									</label>
									<input
										type="date"
										id="end_date"
										name="end_date"
										bind:value={collection.end_date}
										class="input input-bordered w-full"
									/>
								</div>

								<!-- Public Toggle -->
								<div class="form-control">
									<label class="label cursor-pointer justify-start gap-3">
										<input
											type="checkbox"
											class="toggle toggle-primary"
											id="is_public"
											name="is_public"
											bind:checked={collection.is_public}
										/>
										<span class="label-text font-medium">{$t('collection.public_collection')}</span>
									</label>
									<div class="pl-12">
										<span class="text-sm text-base-content/60"
											>{$t('collection.public_collection_description')}</span
										>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Date Warning Alert -->
				{#if !collection.start_date && !collection.end_date}
					<div role="alert" class="alert alert-info shadow-lg">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							class="h-6 w-6 shrink-0 stroke-current"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
						<span>{$t('adventures.collection_no_start_end_date')}</span>
					</div>
				{/if}

				<!-- Share Link Section (only if public and has ID) -->
				{#if collection.is_public && collection.id}
					<div class="card bg-base-100 border border-base-300 shadow-lg">
						<div class="card-body p-6">
							<h3 class="font-semibold text-lg mb-3">{$t('adventures.share_collection')}</h3>
							<div class="flex items-center gap-3">
								<input
									type="text"
									value="{window.location.origin}/collections/{collection.id}"
									readonly
									class="input input-bordered flex-1 font-mono text-sm"
								/>
								<button
									type="button"
									on:click={() => {
										navigator.clipboard.writeText(
											`${window.location.origin}/collections/${collection.id}`
										);
										addToast('success', $t('adventures.link_copied'));
									}}
									class="btn btn-primary gap-2"
								>
									<LinkIcon class="w-4 h-4" />
									{$t('adventures.copy_link')}
								</button>
							</div>
						</div>
					</div>
				{/if}

				<!-- Action Buttons -->
				<div class="flex gap-3 justify-end pt-4">
					<button type="button" class="btn btn-neutral gap-2" on:click={close}>
						<CloseIcon class="w-5 h-5" />
						{$t('about.close')}
					</button>
					<button type="submit" class="btn btn-primary gap-2">
						<SaveIcon class="w-5 h-5" />
						{$t('notes.save')}
					</button>
				</div>
			</form>
		</div>
	</div>
</dialog>
