import { LocateFixed, MapPin } from 'lucide-react-native';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius } from '@/lib/theme';

export function MapPanel() {
  return (
    <View accessibilityLabel="Web map preview" style={styles.map}>
      <View style={[styles.road, styles.roadOne]} />
      <View style={[styles.road, styles.roadTwo]} />
      <View style={styles.pin}>
        <MapPin color={colors.white} fill={colors.emerald} size={30} />
      </View>
      <View style={styles.badge}>
        <LocateFixed color={colors.emerald} size={15} />
        <Text style={styles.badgeText}>Web map preview</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  map: {
    height: 220,
    overflow: 'hidden',
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.large,
    backgroundColor: colors.sky,
  },
  road: {
    position: 'absolute',
    height: 24,
    width: '140%',
    backgroundColor: colors.white,
    opacity: 0.85,
  },
  roadOne: { top: 80, left: -40, transform: [{ rotate: '-12deg' }] },
  roadTwo: { top: 95, left: -80, transform: [{ rotate: '62deg' }] },
  pin: { position: 'absolute', left: '48%', top: 74 },
  badge: {
    position: 'absolute',
    bottom: 12,
    left: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 11,
    paddingVertical: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.white,
  },
  badgeText: { color: colors.forest, fontSize: 11, fontWeight: '800' },
});
