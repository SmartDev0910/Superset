import React, { useEffect, useRef, useState } from 'react';
import { Tabs, Row, Col, Button, Table, Tooltip } from 'antd';
import shortid from 'shortid';
import {
  ShareAltOutlined,
  EditOutlined,
  EyeOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { SupersetClient, SupersetTheme, useTheme } from '@superset-ui/core';
import { TablePaginationConfig } from 'antd/es/table';

interface ViewTablePageProps {
  tables: any[];
  active: number;
}

interface TableParams {
  pagination?: TablePaginationConfig;
}

const ViewTablePage = ({ tables, active }: ViewTablePageProps) => {
  const [columns, setColumns] = useState([] as any);
  const [data, setData] = useState([] as any);
  const [tableParams, setTableParams] = useState<TableParams>({
    pagination: {
      current: 1,
      pageSize: 10,
    },
  });
  const initialItems = tables.map((table, idx) => ({
    label: `Table ${table.table_name}`,
    key: `${idx + 1}`,
  }));
  const [activeKey, setActiveKey] = useState(initialItems[active].key);
  const [items, setItems] = useState(initialItems);

  const loadTableData = () => {
    const data = tables[Number(activeKey) - 1];
    const limit = tableParams.pagination?.pageSize ?? 10;
    const offset =
      (tableParams.pagination?.pageSize ?? 10) *
      ((tableParams.pagination?.current ?? 1) - 1);
    const postPayload = {
      client_id: shortid.generate(),
      database_id: data.database.id,
      json: true,
      runAsync: false,
      schema: data.schema,
      sql: `SELECT * FROM public.${data.table_name} LIMIT ${limit} OFFSET ${offset}`,
      expand_data: true,
    };

    const search = window.location.search || '';
    SupersetClient.post({
      endpoint: `/superset/sql_json/${search}`,
      body: JSON.stringify(postPayload),
      headers: { 'Content-Type': 'application/json' },
      parseMethod: 'json-bigint',
    }).then(({ json }) => {
      setColumns(
        json.columns.map((column: any) => ({
          title: column.name,
          dataIndex: column.name,
          key: column.name,
          align: 'center',
        })),
      );
      setData(json.data);
    });
  };

  const loadPagination = () => {
    const data = tables[Number(activeKey) - 1];
    const postPayload = {
      client_id: shortid.generate(),
      database_id: data.database.id,
      json: true,
      runAsync: false,
      schema: data.schema,
      sql: `SELECT COUNT(*) FROM public.${data.table_name}`,
      expand_data: true,
    };

    const search = window.location.search || '';
    SupersetClient.post({
      endpoint: `/superset/sql_json/${search}`,
      body: JSON.stringify(postPayload),
      headers: { 'Content-Type': 'application/json' },
      parseMethod: 'json-bigint',
    }).then(({ json }) => {
      setTableParams({
        ...tableParams,
        pagination: {
          ...tableParams.pagination,
          total: json.data[0].count,
        },
      });
    });
  };

  const handleTableChange = (pagination: TablePaginationConfig) => {
    setTableParams({ pagination });
  };

  useEffect(() => {
    loadTableData();
    loadPagination();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeKey]);

  useEffect(() => {
    loadTableData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(tableParams)]);

  const newTabIndex = useRef(0);
  const onChange = (newActiveKey: any) => {
    setActiveKey(newActiveKey);
    setTableParams({
      pagination: {
        current: 1,
        pageSize: 10,
      },
    });
  };
  const add = () => {
    const curIndex = newTabIndex.current + 1;
    const newActiveKey = `newTab${curIndex}`;
    const newPanes = [...items];
    newPanes.push({
      label: 'New Tab',
      key: newActiveKey,
    });
    setItems(newPanes);
    setActiveKey(newActiveKey);
  };
  const remove = (targetKey: any) => {
    let newActiveKey = activeKey;
    let lastIndex = -1;
    items.forEach((item, i) => {
      if (item.key === targetKey) {
        lastIndex = i - 1;
      }
    });
    const newPanes = items.filter(item => item.key !== targetKey);
    if (newPanes.length && newActiveKey === targetKey) {
      if (lastIndex >= 0) {
        newActiveKey = newPanes[lastIndex].key;
      } else {
        newActiveKey = newPanes[0].key;
      }
    }
    setItems(newPanes);
    setActiveKey(newActiveKey);
  };
  const onEdit = (targetKey: any, action: any) => {
    if (action === 'add') {
      add();
    } else {
      remove(targetKey);
    }
  };
  const theme: SupersetTheme = useTheme();
  return (
    <Row>
      <Row style={{ width: '100%' }}>
        <Tabs
          type="editable-card"
          onChange={onChange}
          activeKey={activeKey}
          onEdit={onEdit}
        >
          {initialItems.map(item => (
            <Tabs.TabPane tab={item.label} key={item.key} />
          ))}
        </Tabs>
      </Row>
      <Row style={{ width: '100%', marginTop: '10px' }}>
        <Col span={12}>
          <Row>Uploaded on 21 aug 22, 12:00pm IST</Row>
        </Col>
        <Col span={12} style={{ display: 'inline-block' }}>
          <Row style={{ float: 'right' }}>
            <Tooltip placement="top" title="Share">
              <Button
                icon={<ShareAltOutlined />}
                style={{
                  background: 'none',
                  color: theme.colors.quotron.black,
                }}
              />
            </Tooltip>
            <Tooltip placement="top" title="Edit">
              <Button
                icon={<EditOutlined />}
                style={{
                  background: 'none',
                  color: theme.colors.quotron.black,
                  marginLeft: '4px',
                }}
              />
            </Tooltip>
            <Tooltip placement="top" title="View">
              <Button
                icon={<EyeOutlined />}
                style={{
                  background: 'none',
                  color: theme.colors.quotron.black,
                  marginLeft: '4px',
                }}
              />
            </Tooltip>
            <Tooltip placement="top" title="Delete">
              <Button
                icon={<DeleteOutlined />}
                style={{
                  background: 'none',
                  color: theme.colors.quotron.black,
                  marginLeft: '4px',
                }}
              />
            </Tooltip>
          </Row>
        </Col>
      </Row>
      <Table
        columns={columns}
        dataSource={data}
        pagination={tableParams.pagination}
        onChange={handleTableChange}
        style={{ width: '100%', marginTop: '24px' }}
        bordered
      />
    </Row>
  );
};
export default ViewTablePage;
