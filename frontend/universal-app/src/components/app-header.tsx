import { CarFront, CircleUserRound, Radio } from 'lucide-react-native';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius } from '@/lib/theme';
import { useAppStore } from '@/store/app-store';

type ModeButtonProps = {
  label: string;
  selected: boolean;
  onPress: () => void;
};

function ModeButton({ label, selected, onPress }: ModeButtonProps) {
  return (
    <Pressable
      accessibilityRole="tab"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.modeButton, selected && styles.modeButtonActive]}>
      <Text style={[styles.modeText, selected && styles.modeTextActive]}>{label}</Text>
    </Pressable>
  );
}

export function AppHeader() {
  const { mode, setMode, user, signOut } = useAppStore();
  const driverStatus = user?.driver_availability;
  const driverOnline = driverStatus && driverStatus !== 'OFFLINE';

  return (
    <View style={styles.wrap}>
      <View style={styles.topRow}>
        <View style={styles.identity}>
          <View style={styles.logo}>
            <CarFront color={colors.white} size={20} />
          </View>
          <View>
            <Text style={styles.brand}>Mobility Platform</Text>
            <Text style={styles.name}>{user?.full_name}</Text>
          </View>
        </View>
        <Pressable accessibilityLabel="Sign out" onPress={signOut} style={styles.profile}>
          <CircleUserRound color={colors.forest} size={25} />
        </Pressable>
      </View>
      {driverOnline ? (
        <View style={styles.onlineBanner}>
          <Radio color={colors.emerald} size={15} />
          <Text style={styles.onlineText}>Driver status: {driverStatus}</Text>
        </View>
      ) : null}
      <View accessibilityRole="tablist" style={styles.selector}>
        <ModeButton
          label="Rider"
          onPress={() => setMode('rider')}
          selected={mode === 'rider'}
        />
        <ModeButton
          label="Driver"
          onPress={() => setMode('driver')}
          selected={mode === 'driver'}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: colors.sand,
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 10,
    gap: 10,
  },
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  identity: { flexDirection: 'row', alignItems: 'center', gap: 11 },
  logo: {
    width: 40,
    height: 40,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.forest,
  },
  brand: { color: colors.ink, fontWeight: '800', fontSize: 15 },
  name: { color: colors.muted, fontSize: 12, marginTop: 1 },
  profile: { padding: 8 },
  selector: {
    flexDirection: 'row',
    padding: 4,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceRaised,
  },
  modeButton: {
    flex: 1,
    minHeight: 42,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radius.pill,
  },
  modeButtonActive: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
  },
  modeText: { color: colors.muted, fontSize: 15, fontWeight: '700' },
  modeTextActive: { color: colors.ink },
  onlineBanner: { flexDirection: 'row', gap: 7, alignItems: 'center', alignSelf: 'flex-end' },
  onlineText: { color: colors.emerald, fontSize: 11, fontWeight: '800' },
});
