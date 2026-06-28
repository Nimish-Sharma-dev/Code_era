import { Tabs } from 'expo-router';

import { TabIcon } from '@/components/TabIcon';
import { Colors, BottomTabHeight } from '@/constants/theme';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarShowLabel: false,
        tabBarStyle: {
          backgroundColor: Colors.surfaceDim,
          borderTopWidth: 0.5,
          borderTopColor: Colors.navBorder,
          height: BottomTabHeight,
          paddingTop: 8,
        },
        tabBarItemStyle: {
          paddingTop: 2,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ tabBarIcon: ({ focused }) => <TabIcon name="home" label="Home" focused={focused} /> }}
      />
      <Tabs.Screen
        name="markets"
        options={{ tabBarIcon: ({ focused }) => <TabIcon name="markets" label="Markets" focused={focused} /> }}
      />
      <Tabs.Screen
        name="chat"
        options={{ tabBarIcon: ({ focused }) => <TabIcon name="chat" label="Chat" focused={focused} /> }}
      />
      <Tabs.Screen
        name="portfolio"
        options={{ tabBarIcon: ({ focused }) => <TabIcon name="portfolio" label="Portfolio" focused={focused} /> }}
      />
      <Tabs.Screen
        name="tradex"
        options={{ tabBarIcon: ({ focused }) => <TabIcon name="tradex" label="TradeX" focused={focused} /> }}
      />
    </Tabs>
  );
}
