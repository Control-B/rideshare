import { CalendarClock, History, Home, Menu } from 'lucide-react-native';
import { ComponentType } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors } from '@/lib/theme';

export type AppTab = 'home' | 'history' | 'schedule' | 'more';

const tabs: {
  key: AppTab;
  label: string;
  icon: ComponentType<{ color?: string; size?: number }>;
}[] = [
  { key: 'home', label: 'Home', icon: Home },
  { key: 'history', label: 'History', icon: History },
  { key: 'schedule', label: 'Schedule', icon: CalendarClock },
  { key: 'more', label: 'More', icon: Menu },
];

export function BottomTabBar({
  activeTab,
  onChange,
}: {
  activeTab: AppTab;
  onChange: (tab: AppTab) => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <View
      accessibilityRole="tablist"
      style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 8) }]}
    >
      {tabs.map((tab) => {
        const selected = tab.key === activeTab;
        const Icon = tab.icon;
        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            key={tab.key}
            onPress={() => onChange(tab.key)}
            style={styles.tab}
          >
            <View style={[styles.iconFrame, selected && styles.iconFrameActive]}>
              <Icon color={selected ? colors.white : colors.muted} size={21} />
            </View>
            <Text style={[styles.label, selected && styles.labelActive]}>{tab.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    borderTopColor: colors.border,
    borderTopWidth: 1,
    backgroundColor: colors.white,
    paddingHorizontal: 8,
    paddingTop: 8,
  },
  tab: {
    flex: 1,
    minHeight: 54,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
  },
  iconFrame: {
    width: 34,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
  },
  iconFrameActive: { backgroundColor: colors.forest },
  label: { color: colors.muted, fontSize: 10, fontWeight: '700' },
  labelActive: { color: colors.forest },
});
