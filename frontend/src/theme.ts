import type { ThemeConfig } from 'antd';

const theme: ThemeConfig = {
  token: {
    colorPrimary: '#1a56db',
    colorInfo: '#1a56db',
    colorSuccess: '#059669',
    colorWarning: '#d97706',
    colorError: '#dc2626',

    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
    fontSize: 14,

    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,

    boxShadow: '0 1px 3px 0 rgba(0,0,0,0.08), 0 1px 2px -1px rgba(0,0,0,0.08)',
    boxShadowSecondary: '0 4px 12px 0 rgba(0,0,0,0.08), 0 2px 4px -1px rgba(0,0,0,0.06)',

    colorBgLayout: '#f0f4f8',
    colorBgContainer: '#ffffff',
    colorBorderSecondary: '#e2e8f0',
    colorTextBase: '#1e293b',
    colorTextSecondary: '#64748b',

    controlHeight: 36,
    controlHeightLG: 44,
  },
  components: {
    Button: {
      primaryShadow: '0 2px 6px rgba(26,86,219,0.3)',
      fontWeight: 500,
    },
    Card: {
      paddingLG: 20,
    },
    Menu: {
      itemBorderRadius: 6,
      itemHeight: 40,
    },
    Table: {
      headerBg: '#f8fafc',
      headerColor: '#475569',
    },
    Tabs: {
      inkBarColor: '#1a56db',
      itemSelectedColor: '#1a56db',
    },
  },
};

export default theme;
