import { FC } from 'react';
import { Card, Flex } from 'antd';
import Image from 'next/image';
import Link from 'next/link';

import { AppsItemProps } from '@/components/molecules/Apps/AppsItem/AppsItem.props';
import { StyledAppsItemTitle } from '@/components/molecules/Apps/AppsItem/AppsItem.styled';

const AppsItem: FC<AppsItemProps> = ({
  name = '',
  path,
  image = '/img/logo.png',
  className = '',
  ...props
}) => {
  return (
    <Link href={path}>
      <Card hoverable className={`apps-item ${className}`} {...props}>
        <Flex vertical justify='center' align='center'>
          <Image src={image} alt={name} width={55} height={45} />
          <StyledAppsItemTitle>{name}</StyledAppsItemTitle>
        </Flex>
      </Card>
    </Link>
  );
};

export default AppsItem;
