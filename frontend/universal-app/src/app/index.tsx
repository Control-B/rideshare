import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AppHeader } from '@/components/app-header';
import { AuthScreen } from '@/components/auth-screen';
import { DriverHome } from '@/components/driver-home';
import { RiderHome } from '@/components/rider-home';
import { colors } from '@/lib/theme';
import { useAppStore } from '@/store/app-store';

export default function HomeScreen() {
  const token = useAppStore((state) => state.token);
  const mode = useAppStore((state) => state.mode);
  if (!token) return <AuthScreen />;

  return (
    <View style={{ flex: 1, backgroundColor: colors.sand }}>
      <SafeAreaView edges={['top']} style={{ flex: 1 }}>
        <AppHeader />
        {mode === 'rider' ? <RiderHome /> : <DriverHome />}
      </SafeAreaView>
    </View>
  );
}
