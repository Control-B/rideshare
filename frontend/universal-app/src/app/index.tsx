import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AppHeader } from '@/components/app-header';
import { AuthScreen } from '@/components/auth-screen';
import { BottomTabBar, type AppTab } from '@/components/bottom-tab-bar';
import { DriverHome } from '@/components/driver-home';
import { HistoryScreen } from '@/components/history-screen';
import { MoreScreen } from '@/components/more-screen';
import { RiderHome } from '@/components/rider-home';
import { ScheduleScreen } from '@/components/schedule-screen';
import { api } from '@/lib/api';
import { colors } from '@/lib/theme';
import { useAppStore } from '@/store/app-store';

export default function HomeScreen() {
  const token = useAppStore((state) => state.token);
  const mode = useAppStore((state) => state.mode);
  const updateUser = useAppStore((state) => state.updateUser);
  const [activeTab, setActiveTab] = useState<AppTab>('home');

  useEffect(() => {
    if (!token) return;
    api.me(token).then(updateUser).catch(() => {
      // Keep the cached profile available when the API is temporarily unreachable.
    });
  }, [token, updateUser]);

  if (!token) return <AuthScreen />;

  const content = {
    home: mode === 'rider' ? <RiderHome /> : <DriverHome />,
    history: <HistoryScreen />,
    schedule: <ScheduleScreen onStartBooking={() => setActiveTab('home')} />,
    more: <MoreScreen />,
  }[activeTab];

  return (
    <View style={{ flex: 1, backgroundColor: colors.sand }}>
      <SafeAreaView edges={['top']} style={{ flex: 1 }}>
        <AppHeader />
        <View style={{ flex: 1 }}>{content}</View>
        <BottomTabBar activeTab={activeTab} onChange={setActiveTab} />
      </SafeAreaView>
    </View>
  );
}
