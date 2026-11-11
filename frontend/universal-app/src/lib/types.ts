export type InterfaceMode = 'rider' | 'driver';

export type User = {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  driver_approved: boolean;
  driver_availability: string | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type TripEvent = {
  previous_state: string | null;
  new_state: string;
  version: number;
  created_at: string;
};

export type Trip = {
  id: string;
  state: string;
  version: number;
  assigned_driver_id: string | null;
  pickup_address: string;
  destination_address: string;
  fare_cents: number;
  payment_method: 'CASH' | 'SANDBOX_CARD';
  guest_passenger_name: string | null;
  events: TripEvent[];
};

export type Offer = {
  id: string;
  trip_id: string;
  status: string;
  expires_at: string;
  pickup_address: string;
  destination_address: string;
  fare_cents: number;
  pickup_eta_seconds: number | null;
  estimated_trip_miles: number | null;
  expected_earnings_cents: number;
};

export type Quote = {
  fare_cents: number;
  currency: string;
  breakdown: Record<string, number>;
  synthetic: boolean;
};

export type DriverLocation = {
  driver_id: string;
  accepted: boolean;
  anomaly_code: string | null;
  observed_at: string;
  expires_at: string | null;
};

export type NearbyVehicle = {
  vehicle_id: string;
  latitude: number;
  longitude: number;
  updated_at: string;
};
