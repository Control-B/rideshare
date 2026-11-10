import { CalendarClock, ChevronRight, Clock3, Plane, ShieldCheck } from 'lucide-react-native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, radius, shadow } from '@/lib/theme';

export function ScheduleScreen({ onStartBooking }: { onStartBooking: () => void }) {
  return (
    <ScrollView contentContainerStyle={styles.content} style={styles.page}>
      <Text style={styles.eyebrow}>PLAN AHEAD</Text>
      <Text style={styles.title}>Schedule a ride</Text>
      <Text style={styles.subtitle}>
        Start with your route, then choose an eligible pickup window.
      </Text>

      <View style={styles.hero}>
        <View style={styles.iconFrame}>
          <CalendarClock color={colors.emerald} size={30} />
        </View>
        <Text style={styles.heroTitle}>Reserve your next ride</Text>
        <Text style={styles.heroText}>
          Scheduled dispatch depends on driver availability and market rules. Your fare
          and pickup window are confirmed before booking.
        </Text>
        <Pressable onPress={onStartBooking} style={styles.primary}>
          <Text style={styles.primaryText}>Choose pickup and destination</Text>
          <ChevronRight color={colors.white} size={19} />
        </Pressable>
      </View>

      <Text style={styles.sectionTitle}>Designed for</Text>
      <View style={styles.feature}>
        <Plane color={colors.emerald} size={21} />
        <View style={styles.featureCopy}>
          <Text style={styles.featureTitle}>Airport and early rides</Text>
          <Text style={styles.featureText}>Plan ahead for time-sensitive pickups.</Text>
        </View>
      </View>
      <View style={styles.feature}>
        <Clock3 color={colors.emerald} size={21} />
        <View style={styles.featureCopy}>
          <Text style={styles.featureTitle}>Pickup windows</Text>
          <Text style={styles.featureText}>See the confirmed time before you commit.</Text>
        </View>
      </View>
      <View style={styles.feature}>
        <ShieldCheck color={colors.emerald} size={21} />
        <View style={styles.featureCopy}>
          <Text style={styles.featureTitle}>Clear cancellation terms</Text>
          <Text style={styles.featureText}>Rules are disclosed with the scheduled quote.</Text>
        </View>
      </View>
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
  hero: {
    borderRadius: radius.large,
    backgroundColor: colors.white,
    padding: 22,
    gap: 12,
    ...shadow,
  },
  iconFrame: {
    width: 54,
    height: 54,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
    backgroundColor: colors.mist,
  },
  heroTitle: { color: colors.ink, fontSize: 21, fontWeight: '800' },
  heroText: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  primary: {
    minHeight: 52,
    borderRadius: radius.medium,
    backgroundColor: colors.forest,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  primaryText: { color: colors.white, fontWeight: '800' },
  sectionTitle: { color: colors.ink, fontSize: 17, fontWeight: '800', marginTop: 8 },
  feature: {
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.medium,
    backgroundColor: colors.white,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 15,
  },
  featureCopy: { flex: 1 },
  featureTitle: { color: colors.ink, fontWeight: '800' },
  featureText: { color: colors.muted, fontSize: 12, marginTop: 3 },
});
