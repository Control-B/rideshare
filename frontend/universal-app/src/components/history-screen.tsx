import { useQuery } from '@tanstack/react-query';
import { ArrowDown, CarFront, Clock3, ReceiptText } from 'lucide-react-native';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';

import { api } from '@/lib/api';
import { colors, radius, shadow } from '@/lib/theme';
import { useAppStore } from '@/store/app-store';

export function HistoryScreen() {
  const token = useAppStore((state) => state.token)!;
  const userId = useAppStore((state) => state.user!.id);
  const trips = useQuery({
    queryKey: ['trips', userId],
    queryFn: () => api.trips(token),
  });

  return (
    <ScrollView contentContainerStyle={styles.content} style={styles.page}>
      <Text style={styles.eyebrow}>YOUR RIDES</Text>
      <Text style={styles.title}>Trip history</Text>
      <Text style={styles.subtitle}>Receipts and status for rides on this account.</Text>

      {trips.isLoading ? <ActivityIndicator color={colors.emerald} /> : null}
      {trips.error ? <Text style={styles.error}>{trips.error.message}</Text> : null}
      {trips.data?.length === 0 ? (
        <View style={styles.empty}>
          <CarFront color={colors.emerald} size={30} />
          <Text style={styles.emptyTitle}>No rides yet</Text>
          <Text style={styles.emptyText}>Completed and active rides will appear here.</Text>
        </View>
      ) : null}
      {trips.data?.map((trip) => (
        <View key={trip.id} style={styles.card}>
          <View style={styles.cardTop}>
            <View style={styles.status}>
              <Clock3 color={colors.emerald} size={15} />
              <Text style={styles.statusText}>{trip.state.replaceAll('_', ' ')}</Text>
            </View>
            <Text style={styles.fare}>${(trip.fare_cents / 100).toFixed(2)}</Text>
          </View>
          <Text style={styles.routeLabel}>PICKUP</Text>
          <Text style={styles.address}>{trip.pickup_address}</Text>
          <ArrowDown color={colors.muted} size={17} />
          <Text style={styles.routeLabel}>DESTINATION</Text>
          <Text style={styles.address}>{trip.destination_address}</Text>
          <View style={styles.receipt}>
            <ReceiptText color={colors.muted} size={16} />
            <Text style={styles.receiptText}>
              {trip.payment_method === 'CASH' ? 'Cash' : 'Sandbox card'} · Trip{' '}
              {trip.id.slice(0, 8)}
            </Text>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.sand },
  content: {
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
    padding: 18,
    paddingBottom: 36,
    gap: 12,
  },
  eyebrow: { color: colors.emerald, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  title: { color: colors.ink, fontSize: 30, fontWeight: '800' },
  subtitle: { color: colors.muted, fontSize: 14, marginBottom: 8 },
  card: {
    borderRadius: radius.large,
    backgroundColor: colors.white,
    padding: 18,
    gap: 5,
    ...shadow,
  },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  status: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  statusText: { color: colors.emerald, fontSize: 11, fontWeight: '900' },
  fare: { color: colors.forest, fontSize: 18, fontWeight: '900' },
  routeLabel: { color: colors.muted, fontSize: 9, fontWeight: '900', marginTop: 7 },
  address: { color: colors.ink, fontSize: 14, fontWeight: '700' },
  receipt: {
    borderTopColor: colors.border,
    borderTopWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    marginTop: 10,
    paddingTop: 11,
  },
  receiptText: { color: colors.muted, fontSize: 11 },
  empty: {
    alignItems: 'center',
    borderRadius: radius.large,
    backgroundColor: colors.white,
    padding: 30,
    gap: 8,
  },
  emptyTitle: { color: colors.ink, fontSize: 18, fontWeight: '800' },
  emptyText: { color: colors.muted, textAlign: 'center' },
  error: { color: colors.danger },
});
