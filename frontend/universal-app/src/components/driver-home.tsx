import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Banknote,
  CarFront,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  FileCheck2,
  Navigation,
  Power,
  ShieldAlert,
} from 'lucide-react-native';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { api } from '@/lib/api';
import { colors, radius, shadow } from '@/lib/theme';
import type { Trip } from '@/lib/types';
import { useAppStore } from '@/store/app-store';

const NEXT_STATE: Record<string, { state: string; label: string }> = {
  ASSIGNED: { state: 'DRIVER_EN_ROUTE', label: 'Start route to pickup' },
  DRIVER_EN_ROUTE: { state: 'DRIVER_ARRIVED', label: 'Mark arrived' },
  DRIVER_ARRIVED: { state: 'IN_PROGRESS', label: 'Passenger onboard · start trip' },
  IN_PROGRESS: { state: 'COMPLETED', label: 'Complete trip · cash collected' },
};

export function DriverHome() {
  const token = useAppStore((state) => state.token)!;
  const user = useAppStore((state) => state.user)!;
  const updateUser = useAppStore((state) => state.updateUser);
  const queryClient = useQueryClient();
  const approved = user.driver_approved;
  const isOnline = user.driver_availability !== 'OFFLINE';
  const trips = useQuery({
    queryKey: ['trips', user.id],
    queryFn: () => api.trips(token),
    enabled: approved,
    refetchInterval: 5_000,
  });
  const offers = useQuery({
    queryKey: ['offers'],
    queryFn: () => api.offers(token),
    enabled: approved && isOnline,
    refetchInterval: 4_000,
  });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['trips', user.id] });
    queryClient.invalidateQueries({ queryKey: ['offers'] });
  };
  const availability = useMutation({
    mutationFn: () => api.availability(token, isOnline ? 'OFFLINE' : 'ONLINE'),
    onSuccess: updateUser,
  });
  const accept = useMutation({
    mutationFn: (offerId: string) => api.acceptOffer(token, offerId),
    onSuccess: invalidate,
  });
  const transition = useMutation({
    mutationFn: ({ trip, state }: { trip: Trip; state: string }) =>
      api.transition(token, trip.id, state, state === 'COMPLETED'),
    onSuccess: async () => {
      updateUser(await api.me(token));
      invalidate();
    },
  });
  const onboarding = useMutation({
    mutationFn: () => api.startOnboarding(token),
    onSuccess: updateUser,
  });

  if (!approved) {
    const alreadyApplied = user.roles.includes('DRIVER_APPLICANT');
    return (
      <ScrollView contentContainerStyle={styles.content} style={styles.page}>
        <View style={styles.intro}>
          <Text style={styles.eyebrow}>DRIVER MODE</Text>
          <Text style={styles.title}>Drive on your terms.</Text>
          <Text style={styles.subtitle}>
            One identity, with a separate approval path for driving privileges.
          </Text>
        </View>
        <View style={styles.onboardingCard}>
          <View style={styles.onboardingIcon}>
            <FileCheck2 color={colors.emerald} size={28} />
          </View>
          <Text style={styles.cardTitle}>
            {alreadyApplied ? 'Application started' : 'Become a driver'}
          </Text>
          <Text style={styles.body}>
            Driving access requires identity, license, vehicle, insurance, and market
            compliance review. Rider access remains available during review.
          </Text>
          {alreadyApplied ? (
            <View style={styles.pendingBadge}>
              <ShieldAlert color={colors.amber} size={16} />
              <Text style={styles.pendingText}>Awaiting document review</Text>
            </View>
          ) : (
            <Pressable onPress={() => onboarding.mutate()} style={styles.primary}>
              <Text style={styles.primaryText}>Start driver onboarding</Text>
              <ChevronRight color={colors.white} size={19} />
            </Pressable>
          )}
        </View>
      </ScrollView>
    );
  }

  const activeTrip = trips.data?.find((trip) => NEXT_STATE[trip.state]);
  const next = activeTrip ? NEXT_STATE[activeTrip.state] : null;
  return (
    <ScrollView contentContainerStyle={styles.content} style={styles.page}>
      <View style={styles.driverTop}>
        <View>
          <Text style={styles.eyebrow}>DRIVER MODE</Text>
          <Text style={styles.title}>{isOnline ? 'You’re online' : 'You’re offline'}</Text>
          <Text style={styles.subtitle}>
            {user.driver_availability} · Blue demo sedan
          </Text>
        </View>
        <Pressable
          accessibilityLabel={isOnline ? 'Go offline' : 'Go online'}
          disabled={Boolean(activeTrip) || availability.isPending}
          onPress={() => availability.mutate()}
          style={[styles.power, isOnline && styles.powerOnline]}>
          {availability.isPending ? (
            <ActivityIndicator color={isOnline ? colors.white : colors.mint} />
          ) : (
            <Power color={isOnline ? colors.white : colors.mint} size={25} />
          )}
        </Pressable>
      </View>

      {activeTrip && next ? (
        <View accessibilityLiveRegion="polite" style={styles.tripCard}>
          <View style={styles.tripStatus}>
            <Navigation color={colors.mint} size={18} />
            <Text style={styles.tripStatusText}>ACTIVE TRIP · {activeTrip.state}</Text>
          </View>
          <View style={styles.routeRow}>
            <View style={styles.routeLine}>
              <View style={styles.routeDot} />
              <View style={styles.routeStem} />
              <View style={styles.routeSquare} />
            </View>
            <View style={styles.routeCopy}>
              <Text style={styles.routeLabel}>PICKUP</Text>
              <Text style={styles.routeAddress}>{activeTrip.pickup_address}</Text>
              <Text style={styles.routeLabel}>DESTINATION</Text>
              <Text style={styles.routeAddress}>{activeTrip.destination_address}</Text>
            </View>
          </View>
          <View style={styles.cashNotice}>
            <Banknote color={colors.mint} size={19} />
            <Text style={styles.cashNoticeText}>
              Cash due ${(activeTrip.fare_cents / 100).toFixed(2)}
            </Text>
          </View>
          {transition.error ? (
            <Text style={styles.error}>{transition.error.message}</Text>
          ) : null}
          <Pressable
            disabled={transition.isPending}
            onPress={() => transition.mutate({ trip: activeTrip, state: next.state })}
            style={styles.tripAction}>
            {transition.isPending ? (
              <ActivityIndicator color={colors.forest} />
            ) : (
              <>
                <Text style={styles.tripActionText}>{next.label}</Text>
                <ChevronRight color={colors.forest} size={20} />
              </>
            )}
          </Pressable>
        </View>
      ) : (
        <View style={styles.waitingCard}>
          <CarFront color={colors.emerald} size={32} />
          <Text style={styles.cardTitle}>
            {isOnline ? 'Ready for ride offers' : 'Go online when you’re ready'}
          </Text>
          <Text style={styles.body}>
            {isOnline
              ? 'New demo requests appear here automatically.'
              : 'Your location is not collected while offline.'}
          </Text>
        </View>
      )}

      {!activeTrip && offers.data?.map((offer) => (
        <View key={offer.id} style={styles.offerCard}>
          <View style={styles.offerTop}>
            <View>
              <Text style={styles.offerEyebrow}>NEW RIDE OFFER</Text>
              <Text style={styles.offerFare}>${(offer.fare_cents / 100).toFixed(2)}</Text>
            </View>
            <Text style={styles.offerTimer}>90 sec</Text>
          </View>
          <Text style={styles.offerRoute}>{offer.pickup_address}</Text>
          <Text style={styles.offerArrow}>↓</Text>
          <Text style={styles.offerRoute}>{offer.destination_address}</Text>
          {accept.error ? <Text style={styles.error}>{accept.error.message}</Text> : null}
          <Pressable
            disabled={accept.isPending}
            onPress={() => accept.mutate(offer.id)}
            style={styles.primary}>
            <Text style={styles.primaryText}>Accept ride</Text>
            <CheckCircle2 color={colors.white} size={19} />
          </Pressable>
        </View>
      ))}

      <View style={styles.earningsRow}>
        <View style={styles.metric}>
          <CircleDollarSign color={colors.emerald} size={22} />
          <Text style={styles.metricValue}>$0.00</Text>
          <Text style={styles.metricLabel}>Today</Text>
        </View>
        <View style={styles.metric}>
          <Banknote color={colors.emerald} size={22} />
          <Text style={styles.metricValue}>$0.00</Text>
          <Text style={styles.metricLabel}>Cash held</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.sand },
  content: { padding: 18, paddingBottom: 52, gap: 16, width: '100%', maxWidth: 760, alignSelf: 'center' },
  intro: { marginTop: 4 },
  eyebrow: { color: colors.emerald, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  title: { color: colors.ink, fontSize: 30, lineHeight: 36, fontWeight: '800', marginTop: 4 },
  subtitle: { color: colors.muted, fontSize: 14, marginTop: 4 },
  driverTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  power: { width: 58, height: 58, borderRadius: 29, borderWidth: 2, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  powerOnline: { backgroundColor: colors.emerald, borderColor: colors.emerald },
  onboardingCard: { backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: radius.large, padding: 22, gap: 14, ...shadow },
  onboardingIcon: { width: 52, height: 52, borderRadius: 18, backgroundColor: colors.mist, alignItems: 'center', justifyContent: 'center' },
  cardTitle: { color: colors.ink, fontSize: 21, fontWeight: '800' },
  body: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  pendingBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#3B311D', borderRadius: radius.medium, padding: 13 },
  pendingText: { color: colors.amber, fontWeight: '700' },
  primary: { minHeight: 52, borderRadius: radius.medium, backgroundColor: colors.forest, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 9 },
  primaryText: { color: colors.white, fontWeight: '800', fontSize: 15 },
  waitingCard: { alignItems: 'center', backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: radius.large, padding: 28, gap: 9, ...shadow },
  tripCard: { backgroundColor: colors.forest, borderRadius: radius.large, padding: 18, gap: 16, ...shadow },
  tripStatus: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  tripStatusText: { color: colors.mint, fontSize: 11, fontWeight: '900', letterSpacing: 0.7 },
  routeRow: { flexDirection: 'row', gap: 13 },
  routeLine: { alignItems: 'center', width: 14, paddingTop: 5 },
  routeDot: { width: 12, height: 12, borderRadius: 6, borderWidth: 3, borderColor: colors.mint },
  routeStem: { width: 2, height: 38, backgroundColor: colors.emerald },
  routeSquare: { width: 11, height: 11, borderRadius: 2, backgroundColor: colors.mint },
  routeCopy: { flex: 1, gap: 3 },
  routeLabel: { color: colors.mint, fontSize: 9, fontWeight: '900', marginTop: 1 },
  routeAddress: { color: colors.white, fontSize: 15, fontWeight: '700', marginBottom: 9 },
  cashNotice: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#163F7A', borderRadius: radius.small, padding: 12 },
  cashNoticeText: { color: colors.white, fontWeight: '700' },
  tripAction: { minHeight: 54, borderRadius: radius.medium, backgroundColor: colors.white, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  tripActionText: { color: colors.forest, fontWeight: '900' },
  offerCard: { backgroundColor: colors.surface, borderRadius: radius.large, padding: 18, gap: 10, borderWidth: 1, borderColor: colors.emerald, ...shadow },
  offerTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  offerEyebrow: { color: colors.emerald, fontSize: 10, fontWeight: '900', letterSpacing: 0.8 },
  offerFare: { color: colors.ink, fontSize: 26, fontWeight: '900', marginTop: 2 },
  offerTimer: { color: colors.amber, fontWeight: '800', backgroundColor: '#3B311D', paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill },
  offerRoute: { color: colors.ink, fontSize: 14, fontWeight: '700' },
  offerArrow: { color: colors.emerald, fontSize: 18 },
  error: { color: '#FFD0CC', fontSize: 12 },
  earningsRow: { flexDirection: 'row', gap: 12 },
  metric: { flex: 1, backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: radius.medium, padding: 16, gap: 4 },
  metricValue: { color: colors.ink, fontSize: 19, fontWeight: '900' },
  metricLabel: { color: colors.muted, fontSize: 11 },
});
