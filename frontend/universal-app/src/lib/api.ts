import type {
  AuthResponse,
  DriverLocation,
  NearbyVehicle,
  Offer,
  Quote,
  Trip,
  User,
} from '@/lib/types';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export function realtimeUrl(token: string) {
  const base = API_URL.replace(/^http/, 'ws');
  return `${base}/api/v1/realtime?token=${encodeURIComponent(token)}`;
}

type RequestOptions = RequestInit & {
  token?: string | null;
  idempotencyKey?: string;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12_000);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
        ...(options.idempotencyKey
          ? { 'Idempotency-Key': options.idempotencyKey }
          : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : 'Network request failed';
    throw new Error(
      `Cannot reach the API at ${API_URL}. Check EXPO_PUBLIC_API_URL and restart Expo. ${reason}`,
    );
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Request failed' }));
    const detail =
      typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    throw new Error(detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: (token: string) => request<User>('/api/v1/me', { token }),
  quote: (
    token: string,
    data: {
      pickup_address: string;
      destination_address: string;
      pickup_latitude?: number;
      pickup_longitude?: number;
      destination_latitude?: number;
      destination_longitude?: number;
    },
  ) =>
    request<Quote>('/api/v1/quotes', {
      method: 'POST',
      token,
      body: JSON.stringify({ ...data, estimated_miles: 5.4, estimated_minutes: 16 }),
    }),
  book: (
    token: string,
    idempotencyKey: string,
    data: {
      pickup_address: string;
      destination_address: string;
      accepted_fare_cents: number;
      payment_method: 'CASH' | 'SANDBOX_CARD';
      for_someone_else: boolean;
      guest_passenger_name?: string;
      guest_passenger_phone?: string;
      guest_communication_consent?: boolean;
      payment_responsibility: string;
      pickup_latitude?: number;
      pickup_longitude?: number;
      destination_latitude?: number;
      destination_longitude?: number;
    },
  ) =>
    request<Trip>('/api/v1/bookings', {
      method: 'POST',
      token,
      idempotencyKey,
      body: JSON.stringify(data),
    }),
  trips: (token: string) => request<Trip[]>('/api/v1/trips', { token }),
  offers: (token: string) => request<Offer[]>('/api/v1/driver/offers', { token }),
  acceptOffer: (token: string, offerId: string) =>
    request<Trip>(`/api/v1/driver/offers/${offerId}/accept`, {
      method: 'POST',
      token,
    }),
  rejectOffer: (token: string, offerId: string) =>
    request<void>(`/api/v1/driver/offers/${offerId}/reject`, {
      method: 'POST',
      token,
    }),
  updateDriverLocation: (
    token: string,
    location: {
      latitude: number;
      longitude: number;
      accuracy_meters: number;
      speed_mps?: number | null;
      heading_degrees?: number | null;
      observed_at: string;
    },
  ) =>
    request<DriverLocation>('/api/v1/driver/location', {
      method: 'POST',
      token,
      body: JSON.stringify(location),
    }),
  nearbyVehicles: (
    token: string,
    latitude: number,
    longitude: number,
    radiusMiles = 2,
  ) =>
    request<NearbyVehicle[]>(
      `/api/v1/vehicles/nearby?latitude=${latitude}&longitude=${longitude}&radius_miles=${radiusMiles}`,
      { token },
    ),
  availability: (token: string, availability: 'ONLINE' | 'OFFLINE') =>
    request<User>('/api/v1/driver/availability', {
      method: 'PUT',
      token,
      body: JSON.stringify({
        availability: availability === 'ONLINE' ? 'AVAILABLE' : 'OFFLINE',
      }),
    }),
  transition: (
    token: string,
    tripId: string,
    newState: string,
    cashCollected = false,
  ) =>
    request<Trip>(`/api/v1/trips/${tripId}/transition`, {
      method: 'POST',
      token,
      body: JSON.stringify({ new_state: newState, cash_collected: cashCollected }),
    }),
  startOnboarding: (token: string) =>
    request<User>('/api/v1/driver/onboarding', { method: 'POST', token }),
};
