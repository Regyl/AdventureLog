import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Lodging } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };
	let request = await fetch(`${endpoint}/api/lodging/${id.id}/`, {
		headers: {
			Cookie: `sessionid=${event.cookies.get('sessionid')}`
		},
		credentials: 'include'
	});
	if (!request.ok) {
		console.error('Failed to fetch lodging ' + id.id);
		return {
			props: {
				lodging: null
			}
		};
	} else {
		let lodging = (await request.json()) as Lodging;

		return {
			props: {
				lodging
			}
		};
	}
}) satisfies PageServerLoad;

import { redirect, type Actions } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const actions: Actions = {
	delete: async (event) => {
		const id = event.params as { id: string };
		const lodgingId = id.id;

		if (!event.locals.user) {
			return redirect(302, '/login');
		}
		if (!lodgingId) {
			return {
				status: 400,
				error: new Error('Bad request')
			};
		}

		let csrfToken = await fetchCSRFToken();

		let res = await fetch(`${serverEndpoint}/api/lodging/${event.params.id}`, {
			method: 'DELETE',
			headers: {
				Referer: event.url.origin,
				Cookie: `sessionid=${event.cookies.get('sessionid')};
				csrftoken=${csrfToken}`,
				'X-CSRFToken': csrfToken
			},
			credentials: 'include'
		});
		console.log(res);
		if (!res.ok) {
			return {
				status: res.status,
				error: new Error('Failed to delete lodging')
			};
		} else {
			return {
				status: 204
			};
		}
	}
};
