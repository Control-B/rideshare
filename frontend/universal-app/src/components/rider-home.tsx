import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Location from 'expo-location';
import {
  Banknote,
  Clock3,
  LocateFixed,
  Navigation,
  ShieldCheck,
  UserRoundPlus,
} from 'lucide-react-native';
import React from 'react';
import { Controller, useForm, useWatch } from 'react-hook-form';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { z } from 'zod';

import { api } from '@/lib/api';
import { colors, radius, shadow } from '@/lib/theme';
import type { Quote } from '@/lib/types';
import { useRealtimeUpdates } from '@/lib/use-realtime';
import { useAppStore } from '@/store/app-store';
import { MapPanel } from './map-panel';

const bookingSchema = z
  .object({
    pickup: z.string().min(3, 'Enter a pickup location'),
    destination: z.string().min(3, 'Enter a destination'),
    forSomeoneElse: z.boolean(),
    guestName: z.string(),
    guestPhone: z.string(),
  })
  .superRefine((data, context) => {
    if (data.forSomeoneElse && data.guestName.trim().length < 2) {
      context.addIssue({ code: 'custom', path: ['guestName'], message: 'Enter their name' });
    }
    if (data.forSomeoneElse && data.guestPhone.trim().length < 7) {
      context.addIssue({ code: 'custom', path: ['guestPhone'], message: 'Enter a phone number' });
    }
  });

type BookingForm = z.infer<typeof bookingSchema>;

const DEFAULT_CENTER = { latitude: 25.7617, longitude: -80.1918 };

function coordinates(data: BookingForm) {
  const parse = (value: string) => {
    const match = value.match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (!match) return null;
    const latitude = Number(match[1]);
    const longitude = Number(match[2]);
    if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return null;
    return { latitude, longitude };
  };
  const pickup = parse(data.pickup);
  const destination = parse(data.destination);
  if (!pickup || !destination) return {};
  return {
    pickup_latitude: pickup.latitude,
    pickup_longitude: pickup.longitude,
    destination_latitude: destination.latitude,
    destination_longitude: destination.longitude,
  };
}

export function RiderHome() {
  const token = useAppStore((state) => state.token)!;
  const userId = useAppStore((state) => state.user!.id);
  const draft = useAppStore((state) => state.bookingDraft);
  const setDraft = useAppStore((state) => state.setBookingDraft);
  useRealtimeUpdates(token, userId);
  const queryClient = useQueryClient();
  const [quote, setQuote] = React.useState<Quote | null>(null);
  const [locationBusy, setLocationBusy] = React.useState(false);
  const [mapCenter, setMapCenter] = React.useState(DEFAULT_CENTER);
  const {
    control,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<BookingForm>({
    resolver: zodResolver(bookingSchema),
    defaultValues: draft,
  });
  const forSomeoneElse = useWatch({ control, name: 'forSomeoneElse' });
  const trips = useQuery({
    queryKey: ['trips', userId],
    queryFn: () => api.trips(token),
    refetchInterval: 4_000,
  });
  const quoteMutation = useMutation({
    mutationFn: (data: BookingForm) =>
      api.quote(token, {
        pickup_address: data.pickup,
        destination_address: data.destination,
        ...coordinates(data),
      }),
    onSuccess: setQuote,
  });
  const bookingMutation = useMutation({
    mutationFn: (data: BookingForm) =>
      api.book(token, `app-${Date.now()}`, {
        pickup_address: data.pickup,
        destination_address: data.destination,
        accepted_fare_cents: quote!.fare_cents,
        payment_method: 'CASH',
        for_someone_else: data.forSomeoneElse,
        guest_passenger_name: data.forSomeoneElse ? data.guestName : undefined,
        guest_passenger_phone: data.forSomeoneElse ? data.guestPhone : undefined,
        guest_communication_consent: data.forSomeoneElse,
        payment_responsibility: data.forSomeoneElse ? 'PASSENGER' : 'BOOKER',
        ...coordinates(data),
      }),
    onSuccess: () => {
      setQuote(null);
      queryClient.invalidateQueries({ queryKey: ['trips', userId] });
    },
  });
  const nearbyVehicles = useQuery({
    queryKey: ['nearby-vehicles', mapCenter.latitude, mapCenter.longitude],
    queryFn: () =>
      api.nearbyVehicles(token, mapCenter.latitude, mapCenter.longitude),
    refetchInterval: 8_000,
  });

  const submit = (data: BookingForm) => {
    setDraft(data);
    if (quote) bookingMutation.mutate(data);
    else quoteMutation.mutate(data);
  };

  const useCurrentLocation = async () => {
    setLocationBusy(true);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== 'granted') return;
      const result = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      setValue(
        'pickup',
        `${result.coords.latitude.toFixed(5)}, ${result.coords.longitude.toFixed(5)}`,
      );
      setMapCenter({
        latitude: result.coords.latitude,
        longitude: result.coords.longitude,
      });
      setQuote(null);
    } finally {
      setLocationBusy(false);
    }
  };

  const activeTrip = trips.data?.find(
    (trip) => !['COMPLETED', 'CANCELLED', 'FAILED'].includes(trip.state),
  );
  return (
    <ScrollView
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      style={styles.page}>
      <View style={styles.intro}>
        <Text style={styles.eyebrow}>RIDER MODE</Text>
        <Text style={styles.title}>Where to next?</Text>
        <Text style={styles.subtitle}>Clear pricing. Real dispatch. No surprises.</Text>
      </View>

      {activeTrip ? (
        <View accessibilityLiveRegion="polite" style={styles.activeCard}>
          <View style={styles.activeIcon}>
            <Navigation color={colors.white} size={20} />
          </View>
          <View style={styles.activeCopy}>
            <Text style={styles.activeLabel}>ACTIVE RIDE · {activeTrip.state}</Text>
            <Text numberOfLines={1} style={styles.activeRoute}>
              {activeTrip.destination_address}
            </Text>
          </View>
          <Text style={styles.activeFare}>${(activeTrip.fare_cents / 100).toFixed(2)}</Text>
        </View>
      ) : null}

      <MapPanel center={mapCenter} vehicles={nearbyVehicles.data} />

      <View style={styles.bookingCard}>
        <View style={styles.inputRow}>
          <View style={styles.dotPickup} />
          <Controller
            control={control}
            name="pickup"
            render={({ field: { onChange, value } }) => (
              <TextInput
                accessibilityLabel="Pickup location"
                onChangeText={(text) => {
                  onChange(text);
                  setQuote(null);
                }}
                placeholder="Pickup location"
                placeholderTextColor={colors.muted}
                style={styles.locationInput}
                value={value}
              />
            )}
          />
          <Pressable accessibilityLabel="Use current location" onPress={useCurrentLocation}>
            {locationBusy ? (
              <ActivityIndicator color={colors.emerald} />
            ) : (
              <LocateFixed color={colors.emerald} size={21} />
            )}
          </Pressable>
        </View>
        {errors.pickup ? <Text style={styles.error}>{errors.pickup.message}</Text> : null}
        <View style={styles.divider} />
        <View style={styles.inputRow}>
          <View style={styles.dotDestination} />
          <Controller
            control={control}
            name="destination"
            render={({ field: { onChange, value } }) => (
              <TextInput
                accessibilityLabel="Destination"
                onChangeText={(text) => {
                  onChange(text);
                  setQuote(null);
                }}
                placeholder="Where are you going?"
                placeholderTextColor={colors.muted}
                style={styles.locationInput}
                value={value}
              />
            )}
          />
        </View>
        {errors.destination ? (
          <Text style={styles.error}>{errors.destination.message}</Text>
        ) : null}

        <View style={styles.guestRow}>
          <View style={styles.guestLabel}>
            <UserRoundPlus color={colors.forest} size={20} />
            <View>
              <Text style={styles.optionTitle}>Book for someone else</Text>
              <Text style={styles.optionHint}>They can receive ride updates by SMS</Text>
            </View>
          </View>
          <Controller
            control={control}
            name="forSomeoneElse"
            render={({ field: { onChange, value } }) => (
              <Switch
                accessibilityLabel="Book for someone else"
                onValueChange={onChange}
                trackColor={{ true: colors.emerald }}
                value={value}
              />
            )}
          />
        </View>
        {forSomeoneElse ? (
          <View style={styles.guestFields}>
            <Controller
              control={control}
              name="guestName"
              render={({ field: { onChange, value } }) => (
                <TextInput
                  onChangeText={onChange}
                  placeholder="Passenger name"
                  placeholderTextColor={colors.muted}
                  style={styles.secondaryInput}
                  value={value}
                />
              )}
            />
            <Controller
              control={control}
              name="guestPhone"
              render={({ field: { onChange, value } }) => (
                <TextInput
                  keyboardType="phone-pad"
                  onChangeText={onChange}
                  placeholder="Passenger mobile number"
                  placeholderTextColor={colors.muted}
                  style={styles.secondaryInput}
                  value={value}
                />
              )}
            />
            <Text style={styles.consent}>
              Continuing confirms consent to send essential trip messages.
            </Text>
          </View>
        ) : null}

        {quote ? (
          <View style={styles.quoteCard}>
            <View>
              <Text style={styles.quoteLabel}>Demo standard ride</Text>
              <View style={styles.quoteMeta}>
                <Clock3 color={colors.muted} size={14} />
                <Text style={styles.quoteHint}>~16 min · synthetic route</Text>
              </View>
            </View>
            <Text style={styles.quotePrice}>${(quote.fare_cents / 100).toFixed(2)}</Text>
          </View>
        ) : null}
        <View style={styles.paymentRow}>
          <Banknote color={colors.emerald} size={20} />
          <Text style={styles.paymentText}>Cash · pay the driver after the ride</Text>
        </View>
        {(quoteMutation.error || bookingMutation.error) && (
          <Text style={styles.error}>
            {(quoteMutation.error || bookingMutation.error)?.message}
          </Text>
        )}
        <Pressable
          disabled={quoteMutation.isPending || bookingMutation.isPending}
          onPress={handleSubmit(submit)}
          style={({ pressed }) => [styles.primary, pressed && styles.pressed]}>
          {quoteMutation.isPending || bookingMutation.isPending ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.primaryText}>
              {quote ? `Request ride · $${(quote.fare_cents / 100).toFixed(2)}` : 'See fare'}
            </Text>
          )}
        </Pressable>
      </View>
      <View style={styles.safety}>
        <ShieldCheck color={colors.emerald} size={20} />
        <Text style={styles.safetyText}>
          Trip state and driver assignment are verified by the server.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.sand },
  content: { padding: 18, paddingBottom: 52, gap: 16, width: '100%', maxWidth: 760, alignSelf: 'center' },
  intro: { marginTop: 4 },
  eyebrow: { color: colors.emerald, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  title: { color: colors.ink, fontSize: 32, lineHeight: 38, fontWeight: '800', marginTop: 4 },
  subtitle: { color: colors.muted, fontSize: 15, marginTop: 3 },
  activeCard: { backgroundColor: colors.forest, borderRadius: radius.medium, padding: 14, flexDirection: 'row', alignItems: 'center', gap: 12 },
  activeIcon: { width: 38, height: 38, borderRadius: 12, backgroundColor: colors.emerald, alignItems: 'center', justifyContent: 'center' },
  activeCopy: { flex: 1 },
  activeLabel: { color: colors.mint, fontSize: 10, fontWeight: '900', letterSpacing: 0.7 },
  activeRoute: { color: colors.white, fontSize: 14, fontWeight: '700', marginTop: 3 },
  activeFare: { color: colors.white, fontWeight: '800' },
  bookingCard: { backgroundColor: colors.white, borderRadius: radius.large, padding: 18, gap: 12, ...shadow },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  dotPickup: { width: 12, height: 12, borderRadius: 6, borderWidth: 3, borderColor: colors.emerald },
  dotDestination: { width: 12, height: 12, borderRadius: 3, backgroundColor: colors.forest },
  locationInput: { flex: 1, minHeight: 46, color: colors.ink, fontSize: 16, fontWeight: '600' },
  divider: { height: 1, backgroundColor: colors.border, marginLeft: 24 },
  error: { color: colors.danger, fontSize: 12 },
  guestRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 14 },
  guestLabel: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 },
  optionTitle: { color: colors.ink, fontSize: 14, fontWeight: '700' },
  optionHint: { color: colors.muted, fontSize: 11, marginTop: 2 },
  guestFields: { gap: 8 },
  secondaryInput: { minHeight: 46, borderRadius: radius.small, backgroundColor: colors.mist, paddingHorizontal: 14, color: colors.ink },
  consent: { color: colors.muted, fontSize: 10, lineHeight: 15 },
  quoteCard: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.mist, borderRadius: radius.medium, padding: 14 },
  quoteLabel: { color: colors.ink, fontWeight: '800' },
  quoteMeta: { flexDirection: 'row', gap: 5, alignItems: 'center', marginTop: 4 },
  quoteHint: { color: colors.muted, fontSize: 11 },
  quotePrice: { color: colors.forest, fontSize: 22, fontWeight: '900' },
  paymentRow: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  paymentText: { color: colors.muted, fontSize: 13 },
  primary: { minHeight: 54, borderRadius: radius.medium, backgroundColor: colors.forest, alignItems: 'center', justifyContent: 'center' },
  primaryText: { color: colors.white, fontSize: 16, fontWeight: '800' },
  pressed: { opacity: 0.82 },
  safety: { flexDirection: 'row', alignItems: 'center', gap: 9, paddingHorizontal: 8 },
  safetyText: { flex: 1, color: colors.muted, fontSize: 12, lineHeight: 18 },
});
