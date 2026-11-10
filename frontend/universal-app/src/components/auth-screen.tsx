import { useMutation } from '@tanstack/react-query';
import { ArrowRight, CarFront, ShieldCheck } from 'lucide-react-native';
import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { api } from '@/lib/api';
import { colors, radius, shadow } from '@/lib/theme';
import { useAppStore } from '@/store/app-store';

export function AuthScreen() {
  const setSession = useAppStore((state) => state.setSession);
  const [email, setEmail] = useState('rider@example.test');
  const [password, setPassword] = useState('demo-pass-123');
  const login = useMutation({
    mutationFn: () => api.login(email.trim(), password),
    onSuccess: (data) => setSession(data.access_token, data.user),
  });

  const chooseDemo = (kind: 'rider' | 'driver') => {
    setEmail(`${kind}@example.test`);
    setPassword('demo-pass-123');
  };

  return (
    <SafeAreaView style={styles.page}>
      <View style={styles.shell}>
        <View style={styles.brandMark}>
          <CarFront color={colors.white} size={28} />
        </View>
        <Text style={styles.eyebrow}>CONFIGURABLE MOBILITY PLATFORM</Text>
        <Text style={styles.title}>One account.{'\n'}Every journey.</Text>
        <Text style={styles.subtitle}>
          Book a ride or drive—all from one secure account.
        </Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Welcome back</Text>
          <Text style={styles.label}>Email</Text>
          <TextInput
            accessibilityLabel="Email"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            onChangeText={setEmail}
            style={styles.input}
            value={email}
          />
          <Text style={styles.label}>Password</Text>
          <TextInput
            accessibilityLabel="Password"
            onChangeText={setPassword}
            secureTextEntry
            style={styles.input}
            value={password}
          />
          {login.error ? <Text style={styles.error}>{login.error.message}</Text> : null}
          <Pressable
            accessibilityRole="button"
            disabled={login.isPending}
            onPress={() => login.mutate()}
            style={({ pressed }) => [styles.primary, pressed && styles.pressed]}>
            {login.isPending ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <>
                <Text style={styles.primaryText}>Continue</Text>
                <ArrowRight color={colors.white} size={20} />
              </>
            )}
          </Pressable>
          <View style={styles.demoRow}>
            <Pressable onPress={() => chooseDemo('rider')} style={styles.demoButton}>
              <Text style={styles.demoText}>Use rider demo</Text>
            </Pressable>
            <Pressable onPress={() => chooseDemo('driver')} style={styles.demoButton}>
              <Text style={styles.demoText}>Use driver demo</Text>
            </Pressable>
          </View>
        </View>
        <View style={styles.trustRow}>
          <ShieldCheck color={colors.emerald} size={18} />
          <Text style={styles.trustText}>Demo credentials use synthetic data only.</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.sand },
  shell: {
    flex: 1,
    width: '100%',
    maxWidth: 520,
    alignSelf: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  brandMark: {
    width: 52,
    height: 52,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.forest,
    marginBottom: 24,
  },
  eyebrow: { color: colors.emerald, fontSize: 12, fontWeight: '800', letterSpacing: 1.4 },
  title: { color: colors.ink, fontSize: 44, lineHeight: 48, fontWeight: '800', marginTop: 10 },
  subtitle: { color: colors.muted, fontSize: 17, lineHeight: 25, marginTop: 12, marginBottom: 28 },
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.large,
    padding: 22,
    gap: 10,
    ...shadow,
  },
  cardTitle: { color: colors.ink, fontSize: 22, fontWeight: '700', marginBottom: 8 },
  label: { color: colors.forest, fontSize: 13, fontWeight: '700' },
  input: {
    minHeight: 52,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.medium,
    paddingHorizontal: 16,
    fontSize: 16,
    color: colors.ink,
    backgroundColor: colors.mist,
    marginBottom: 4,
  },
  primary: {
    minHeight: 54,
    borderRadius: radius.medium,
    backgroundColor: colors.forest,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 10,
    marginTop: 8,
  },
  primaryText: { color: colors.white, fontSize: 16, fontWeight: '800' },
  pressed: { opacity: 0.82 },
  error: { color: colors.danger, lineHeight: 20 },
  demoRow: { flexDirection: 'row', gap: 8, marginTop: 4 },
  demoButton: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 11,
    borderRadius: radius.small,
    backgroundColor: colors.mist,
  },
  demoText: { color: colors.emerald, fontSize: 13, fontWeight: '700' },
  trustRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 20 },
  trustText: { color: colors.muted, fontSize: 13 },
});
