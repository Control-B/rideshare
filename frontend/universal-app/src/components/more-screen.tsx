import {
  Bell,
  ChevronRight,
  CircleHelp,
  CreditCard,
  FileText,
  LogOut,
  Settings,
  ShieldCheck,
  UserRound,
} from 'lucide-react-native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, radius, shadow } from '@/lib/theme';
import { useAppStore } from '@/store/app-store';

const menuItems = [
  { label: 'Profile and personal information', icon: UserRound },
  { label: 'Payment methods', icon: CreditCard },
  { label: 'Notifications', icon: Bell },
  { label: 'Privacy and safety', icon: ShieldCheck },
  { label: 'Settings', icon: Settings },
  { label: 'Help and support', icon: CircleHelp },
  { label: 'Legal and accessibility', icon: FileText },
];

export function MoreScreen() {
  const user = useAppStore((state) => state.user)!;
  const signOut = useAppStore((state) => state.signOut);

  return (
    <ScrollView contentContainerStyle={styles.content} style={styles.page}>
      <Text style={styles.eyebrow}>ACCOUNT</Text>
      <Text style={styles.title}>More</Text>

      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{user.full_name.charAt(0).toUpperCase()}</Text>
        </View>
        <View style={styles.profileCopy}>
          <Text style={styles.name}>{user.full_name}</Text>
          <Text style={styles.email}>{user.email}</Text>
          <Text style={styles.roles}>{user.roles.join(' · ')}</Text>
        </View>
        <ChevronRight color={colors.muted} size={20} />
      </View>

      <View style={styles.menuCard}>
        {menuItems.map((item, index) => {
          const Icon = item.icon;
          return (
            <Pressable
              accessibilityRole="button"
              key={item.label}
              style={[styles.row, index < menuItems.length - 1 && styles.rowBorder]}
            >
              <View style={styles.rowIcon}>
                <Icon color={colors.emerald} size={19} />
              </View>
              <Text style={styles.rowLabel}>{item.label}</Text>
              <ChevronRight color={colors.muted} size={18} />
            </Pressable>
          );
        })}
      </View>

      <Pressable accessibilityRole="button" onPress={signOut} style={styles.signOut}>
        <LogOut color={colors.danger} size={19} />
        <Text style={styles.signOutText}>Sign out</Text>
      </Pressable>
      <Text style={styles.version}>Mobility Platform · Demo build 0.1.0</Text>
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
    gap: 14,
  },
  eyebrow: { color: colors.emerald, fontSize: 11, fontWeight: '900', letterSpacing: 1.2 },
  title: { color: colors.ink, fontSize: 30, fontWeight: '800' },
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 13,
    borderRadius: radius.large,
    backgroundColor: colors.white,
    padding: 18,
    ...shadow,
  },
  avatar: {
    width: 52,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
    backgroundColor: colors.forest,
  },
  avatarText: { color: colors.white, fontSize: 21, fontWeight: '900' },
  profileCopy: { flex: 1 },
  name: { color: colors.ink, fontSize: 18, fontWeight: '900' },
  email: { color: colors.muted, fontSize: 12, marginTop: 2 },
  roles: { color: colors.emerald, fontSize: 10, fontWeight: '800', marginTop: 5 },
  menuCard: {
    overflow: 'hidden',
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.large,
    backgroundColor: colors.white,
  },
  row: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
    marginHorizontal: 14,
  },
  rowBorder: { borderBottomColor: colors.border, borderBottomWidth: 1 },
  rowIcon: {
    width: 34,
    height: 34,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 11,
    backgroundColor: colors.mist,
  },
  rowLabel: { flex: 1, color: colors.ink, fontSize: 14, fontWeight: '700' },
  signOut: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderColor: '#F3C2BE',
    borderWidth: 1,
    borderRadius: radius.medium,
    backgroundColor: '#FFF7F6',
  },
  signOutText: { color: colors.danger, fontWeight: '800' },
  version: { color: colors.muted, fontSize: 10, textAlign: 'center' },
});
