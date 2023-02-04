import React, { useState } from 'react';
import { Layout, Menu } from 'antd';
import { SupersetTheme, useTheme } from '@superset-ui/core';
import {
  HomeOutlined,
  SearchOutlined,
  DatabaseOutlined,
  SettingOutlined,
  BellOutlined,
} from '@ant-design/icons';
import UploadCsv from 'src/views/components/Upload';
import ContentPage from './pages/ContentPage';
import ViewSearchPage from './pages/ViewSearchPage';
import HeaderViewTablePage from './pages/HeaderViewTablePage';
import ViewTablePage from './pages/ViewTablePage';

const { Header, Content, Sider } = Layout;

const DatamanageList = () => {
  const theme: SupersetTheme = useTheme();

  const [outLined, setoutLined] = useState('1');

  const handleOutLined = (ev: any) => {
    setoutLined(ev.key);
  };

  const [viewTable, setViewTable] = useState(false);
  const [tables, setTables] = useState([] as any);
  const [activeIdx, setActiveIdx] = useState(0);

  const onViewTable = (data: any) => {
    const idx = tables.findIndex((table: any) => table.id === data.id);
    if (idx === -1) {
      setTables([...tables, data]);
    }
    setActiveIdx(idx === -1 ? tables.length : idx);
    setViewTable(true);
  };

  const onBack = () => {
    setViewTable(false);
    setActiveIdx(0);
  };

  // @ts-ignore
  // @ts-ignore
  // @ts-ignore
  // @ts-ignore
  // @ts-ignore
  return (
    <Layout>
      <Sider
        collapsible
        collapsed
        trigger={null}
        theme="light"
        style={{
          background: theme.colors.quotron.gray_white,
        }}
      >
        <Menu
          onClick={handleOutLined}
          // defaultSelectedKeys={[outLined]}
          defaultOpenKeys={['sub1']}
          mode="inline"
          style={{
            background: theme.colors.quotron.gray_white,
            height: '100%',
          }}
        >
          <Menu.Item
            key={1}
            className={`${outLined === '1' ? 'ant-menu-item-selected' : ''}`}
            icon={<HomeOutlined />}
          />
          <Menu.Item
            key={2}
            className={`${outLined === '2' ? 'ant-menu-item-selected' : ''}`}
            icon={<SearchOutlined />}
          />
          <Menu.Item
            key={3}
            className={`${outLined === '3' ? 'ant-menu-item-selected' : ''}`}
            icon={<DatabaseOutlined />}
          />
          <Menu.Item
            key={4}
            icon={<BellOutlined />}
            style={{ position: 'absolute', bottom: 70 }}
          />
          <Menu.Item
            key={5}
            icon={<SettingOutlined />}
            style={{ position: 'absolute', bottom: 20 }}
          />
        </Menu>
      </Sider>
      {outLined === '2' && (
        <Layout>
          <ViewSearchPage />
        </Layout>
      )}
      {outLined === '3' && (
        <Layout>
          <UploadCsv />
        </Layout>
      )}
      {outLined === '1' && (
        <Layout>
          <Header
            style={{
              padding: '48px',
              background: theme.colors.quotron.white,
            }}
          >
            {viewTable && <HeaderViewTablePage onBack={onBack} />}
          </Header>

          <Content
            style={{
              minHeight: '90vh',
              background: theme.colors.quotron.white,
              padding: '48px',
            }}
          >
            {!viewTable && <ContentPage onViewTable={onViewTable} />}
            {viewTable && <ViewTablePage tables={tables} active={activeIdx} />}
          </Content>
        </Layout>
      )}
    </Layout>
  );
};
export default DatamanageList;
